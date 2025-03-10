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
$ ros-launch-analyzer <launchファイル（ディレクトリ）のパス> [--output <出力ファイル名>] [--ros-ws <ROSワークスペースのパス>]
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


## 必要条件

- Python 3.8以上
- Graphviz（システムにインストールされている必要があります）
