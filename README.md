# ros-launch-analyzer

## 概要

ros-launch-analyzerは、ROSのlaunchファイルの依存関係を分析してグラフを生成するツールです。

ROS1がインストールされていない環境で使うことを想定したツールのため、ROSに依存せずに動かせます。

（そのためROSがインストールされている環境ならば簡単にパスが見つかるようなパッケージも、見つかりにくいことがあります）

## 機能

- launchファイル間の依存関係を解析
- ROSノードの依存関係を解析
- 依存関係をGraphvizを使ってグラフ化
- シンプルグラフと詳細グラフの生成
- ノード情報のCSV出力

## インストール

```bash
pip install ros-launch-analyzer
```

## 実行方法

### CLIとして

```sh-session
$ ros-launch-analyzer <launchファイルまたはディレクトリのパス> [--output <出力ファイル名>] [--ros-ws <ROSワークスペースのパス>]
```

**解析対象の指定について:**

*   **ディレクトリを指定した場合:**
    指定されたディレクトリ以下の全ての `.launch` および `.launch.xml` ファイルを再帰的に検索し、それらのファイル間の依存関係（`<include>` タグによる参照）を全て解析します。間接的な依存関係も含まれます。
    ```sh-session
    # 例: mycobot_gazebo パッケージの launch ディレクトリ全体を解析
    $ ros-launch-analyzer catkin_ws/src/mycobot_ros/mycobot_gazebo/launch --ros-ws "$(pwd)/catkin_ws"
    ```

*   **単一のlaunchファイルを指定した場合:**
    指定された launch ファイルと、そのファイルが **直接 `<include>` タグで参照している launch ファイルのみ** を対象として解析し、グラフを生成します。指定ファイルから見て2階層目以降の間接的な依存関係はグラフに含まれません。これは、特定のファイル周辺の直接的な依存関係に絞って確認したい場合に便利です。
    ```sh-session
    # 例: demo.launch とそれが直接 include するファイルのみを解析
    $ ros-launch-analyzer catkin_ws/src/mycobot_ros/mycobot_move_it_config/launch/demo.launch --ros-ws "$(pwd)/catkin_ws"
    ```

mycobot_rosのlaunchファイルを解析する例 (ディレクトリ指定)

```sh-session
$ cd /tmp
$ mkdir -p catkin_ws/src
$ git clone https://github.com/Tiryoh/mycobot_ros.git catkin_ws/src/mycobot_ros
$ ros-launch-analyzer catkin_ws/src/mycobot_ros/mycobot_gazebo/launch --ros-ws "$(pwd)/catkin_ws"
```

### Pythonモジュールとして

```python
from ros_launch_analyzer.analyzer import LaunchAnalyzer

# 解析器の初期化
analyzer = LaunchAnalyzer("/path/to/launch/dir", "/path/to/catkin_ws")

# launchファイルの解析
analyzer.parse_launch_file("/path/to/your.launch")

# グラフの生成
analyzer.create_graph("output_filename")
# または
analyzer.create_simple_graph("output_filename")  # シンプルグラフのみ
analyzer.create_full_graph("output_filename")    # 詳細グラフのみ
```

## 出力

以下のファイルを生成し出力します。  
dotファイルは[xdot](https://github.com/jrfonseca/xdot.py)や[VSCodeの拡張機能（Graphviz Interactive Preview）](https://marketplace.visualstudio.com/items?itemName=tintinweb.graphviz-interactive-preview)などで表示できます。  
生成されたファイルはClaudeなどでdrawioのフォーマットに変換して使用すると便利です。

- `ros_nodes_graph_simple.dot`
  - launchファイルの依存関係を表すGraphvizのdotファイル
- `ros_nodes_graph_simple.pdf`
  - 上記のdotファイルをレンダリングしたPDF
- `ros_nodes_graph.dot`
  - launchファイル（ROSパッケージも含む）の依存関係を表すGraphvizのdotファイル
- `ros_nodes_graph.pdf`
  - 上記のdotファイルをレンダリングしたPDF
- `ros_nodes_graph_nodes.csv`
  - launchファイルのノード名とパッケージ名を出力したCSVファイル

### mycobot_rosを解析した結果

simpleグラフ  
![Image](https://github.com/user-attachments/assets/9bf40e5f-a1ca-45ce-99e6-eadc0f750656)

fullグラフ  
![Image](https://github.com/user-attachments/assets/b1da58d3-14cd-41f2-b89f-9d8559864731)

simpleグラフをdrawioのフォーマット（[flow.drawio.txt](https://github.com/user-attachments/files/19829833/flow.drawio.txt)）に変換したもの  
![Image](https://github.com/user-attachments/assets/24e8202d-6d9d-4899-ae57-28c519b77263)

## 必要条件

- Python 3.8以上
- Graphviz（システムにインストールされている必要があります）

## ライセンス

本プロジェクトは[MITライセンス](LICENSE)のもとで公開されています。
