#!/usr/bin/env python3
"""
ROSのlaunchファイルを解析し、依存関係グラフを生成するモジュール

SPDX-License-Identifier: MIT
(C) 2025 Daisuke Sato
"""

import glob
import os
import re
import xml.etree.ElementTree as ET

import graphviz


class LaunchAnalyzer:
    """ROSのlaunchファイルを解析するクラス"""

    def __init__(self, launch_dir: str, ros_ws_dir: str = ""):
        """初期化

        Args:
            launch_dir (str): launchファイルのディレクトリ
            ros_ws_dir (str, optional): ROSワークスペースのディレクトリ. Defaults to "".
        """
        self.launch_dir = os.path.abspath(launch_dir)
        self.ros_ws_dir = ros_ws_dir if ros_ws_dir else os.path.expanduser("~/catkin_ws")
        self.launch_dependencies: dict[str, list[tuple[str, str]]] = {}  # launchファイルの依存関係
        self.nodes: dict[str, dict[str, str]] = {}  # ノード情報
        self.pkg_path_cache: dict[str, str] = {}  # パッケージパスのキャッシュ
        self.cluster_id_cache: dict[str, str] = {}  # クラスタIDのキャッシュ

        print(f"🔍 ROSワークスペース: {self.ros_ws_dir}")
        print(f"📂 launchディレクトリ: {self.launch_dir}")

    def _generate_cluster_id(self, launch_file: str) -> str:
        """一貫性のあるクラスタIDを生成

        Args:
            launch_file (str): launchファイルの絶対パス

        Returns:
            str: クラスタID
        """
        base_name = os.path.basename(launch_file)
        # cluster_プレフィックスを除去し、ハッシュ値のみを返す
        return f"{abs(hash(base_name))}"

    def _get_cluster_id(self, launch_file: str) -> str:
        """キャッシュからクラスタIDを取得、なければ生成

        Args:
            launch_file (str): launchファイルの絶対パス

        Returns:
            str: クラスタID
        """
        if launch_file not in self.cluster_id_cache:
            self.cluster_id_cache[launch_file] = self._generate_cluster_id(launch_file)
            print(f"   🔑 新規クラスタID生成: {os.path.basename(launch_file)} -> "
                  f"{self.cluster_id_cache[launch_file]}")
        else:
            print(f"   💾 キャッシュからクラスタID取得: {os.path.basename(launch_file)} -> "
                  f"{self.cluster_id_cache[launch_file]}")
        return self.cluster_id_cache[launch_file]

    def _find_package_path(self, pkg_name: str) -> str:
        """ROSパッケージのパスを探索

        Args:
            pkg_name (str): パッケージ名

        Returns:
            str: パッケージのパス。見つからない場合は空文字列
        """
        # キャッシュにあればそれを返す
        if pkg_name in self.pkg_path_cache:
            print(f"      💾 キャッシュからパッケージパスを取得: {pkg_name}")
            return self.pkg_path_cache[pkg_name]

        print(f"      🔍 パッケージを検索: {pkg_name}")

        # ホームディレクトリ配下のcatkin_ws/srcを探索
        ros_ws_pattern = os.path.join(self.ros_ws_dir, 'src/**', pkg_name)
        matches = glob.glob(ros_ws_pattern, recursive=True)

        print(f"      📂 検索パターン: {ros_ws_pattern}")

        # 見つかったパッケージを表示
        if matches:
            print("      📍 見つかったパッケージ候補:")
            for match in matches:
                print(f"         - {match}")

        # package.xmlがある有効なパッケージを探す
        valid_paths = [p for p in matches if os.path.exists(os.path.join(p, 'package.xml'))]

        if valid_paths:
            pkg_path = valid_paths[0]  # 最初に見つかったものを使用
            print(f"      ✅ 有効なパッケージを発見: {pkg_path}")
            self.pkg_path_cache[pkg_name] = pkg_path  # キャッシュに保存
            return pkg_path

        print(f"      ❌ 有効なパッケージが見つかりません: {pkg_name}")
        return ""

    def _resolve_find_expression(self, text: str) -> str:
        """$(find pkg_name)形式の式を解決

        Args:
            text (str): 解決する文字列

        Returns:
            str: 解決後の文字列
        """
        print("\n      🔍 $(find)式の解決を開始:")
        print(f"         📄 入力テキスト: '{text}'")

        # 入力テキストの検証
        if not text:
            print("         ⚠️ 入力テキストが空です")
            return text

        # $(find pkg_name)のパターンを検出
        find_pattern = r'\$\(find\s+([^)]+)\)'
        print(f"         🎯 使用する正規表現パターン: {find_pattern}")

        try:
            matches = re.findall(find_pattern, text)
            print(f"         🔎 検出されたマッチ数: {len(matches)}")

            if not matches:
                print("         ℹ️ $(find)式は検出されませんでした")
                return text

            print("         📋 検出されたパッケージ名:")
            for i, pkg_name in enumerate(matches, 1):
                print(f"            {i}. '{pkg_name}'")

            resolved_text = text
            for pkg_name in matches:
                original_expr = f'$(find {pkg_name})'
                print(f"\n         🔄 パッケージ名の解決: '{pkg_name}'")
                print(f"            📌 置換対象: '{original_expr}'")

                pkg_path = self._find_package_path(pkg_name.strip())
                if pkg_path:
                    # $(find pkg_name)をパッケージパスで置換
                    resolved_text = resolved_text.replace(original_expr, pkg_path)
                    print("            ✅ 解決成功:")
                    print(f"               - 前: '{original_expr}'")
                    print(f"               - 後: '{pkg_path}'")
                else:
                    print(f"            ❌ パッケージが見つからないため置換をスキップ: {pkg_name}")

            print("\n         📝 最終的な解決結果:")
            print(f"            - 変換前: '{text}'")
            print(f"            - 変換後: '{resolved_text}'")

            return resolved_text

        except re.error as e:
            print(f"         ❌ 正規表現エラー: {str(e)}")
            return text
        except Exception as e:
            print(f"         ❌ 予期せぬエラー: {str(e)}")
            return text

    def _extract_package_name(self, path: str) -> str:
        """パスから$(find package_name)のパッケージ名を抽出

        Args:
            path (str): 解析対象のパス

        Returns:
            str: パッケージ名。見つからない場合は空文字列
        """
        find_pattern = r'\$\(find\s+([^)]+)\)'
        matches = re.findall(find_pattern, path)
        if matches:
            return str(matches[0].strip())
        return ""

    def parse_launch_file(self, launch_file: str) -> None:
        """launchファイルを解析してノードとその依存関係を抽出

        Args:
            launch_file (str): 解析対象のlaunchファイルパス
        """
        if not os.path.exists(launch_file):
            print(f"⚠️  警告: launchファイルが見つかりません: {launch_file}")
            return

        abs_launch_file = os.path.abspath(launch_file)
        print(f"\n🔍 解析開始: {abs_launch_file}")

        # 新規ファイルの場合のみ初期化
        if abs_launch_file not in self.launch_dependencies:
            print(f"   📝 新規launchファイルを登録: {abs_launch_file}")
            self.launch_dependencies[abs_launch_file] = []
        else:
            print(f"   ⚠️ 既に解析済みのファイル: {abs_launch_file}")
            return  # 循環参照防止

        try:
            tree = ET.parse(launch_file)
            root = tree.getroot()

            # includeタグの解析（他のlaunchファイルの参照）
            includes = root.findall('.//include')
            print(f"   🔎 includeタグ数: {len(includes)}")

            for i, include in enumerate(includes, 1):
                print(f"\n   📂 includeタグ {i}/{len(includes)} の解析:")
                print(f"      🔍 タグの属性: {include.attrib}")

                # includeタグの中身を表示
                include_content = ET.tostring(include, encoding='unicode')
                print(f"      📄 タグの内容:\n{include_content}")

                # fileパスを属性から取得
                file_path = include.get('file')
                if file_path is None:
                    print("      ❌ file属性が見つかりません")
                    continue

                print(f"      📝 file属性の値: '{file_path}'")

                if not file_path:
                    print("      ⚠️ fileパスが空です")
                    continue

                original_path = file_path.strip()
                print(f"      🎯 検出されたパス: '{original_path}'")

                # パッケージ名を抽出
                pkg_name = self._extract_package_name(original_path)
                if pkg_name:
                    print(f"      📦 検出されたパッケージ名: {pkg_name}")

                # パスの解決
                resolved_path = self._resolve_find_expression(original_path)

                if resolved_path != original_path:
                    print(f"      🔄 パス解決: {original_path} -> {resolved_path}")
                    included_path = resolved_path
                else:
                    included_path = os.path.join(os.path.dirname(launch_file), original_path)
                    print("      💫 相対パスの解決:")
                    print(f"      - 基準ディレクトリ: {os.path.dirname(launch_file)}")
                    print(f"      - 解決後のパス: {included_path}")

                if os.path.exists(included_path):
                    abs_included_path = os.path.abspath(included_path)
                    print(f"      ✅ ファイルの存在を確認: {abs_included_path}")

                    # 依存関係の登録
                    dependency = (abs_included_path, pkg_name)
                    if dependency not in self.launch_dependencies[abs_launch_file]:
                        self.launch_dependencies[abs_launch_file].append(dependency)
                        print(f"      ➕ 依存関係を登録: {abs_launch_file} -> {abs_included_path} ({pkg_name})")
                        print(f"      📊 現在の依存関係数: {len(self.launch_dependencies[abs_launch_file])}")
                    else:
                        print(f"      ⚠️ 既に登録済みの依存関係: {abs_included_path}")

                    self.parse_launch_file(abs_included_path)
                else:
                    print(f"      ❌ ファイルが見つかりません: {included_path}")
                    print("      💡 試行したパス:")
                    print(f"         - 絶対パス: {os.path.abspath(included_path)}")
                    print(f"         - 現在のディレクトリ: {os.getcwd()}")
                    print(f"         - ファイルの存在確認結果: {os.path.exists(included_path)}")

            print("\n   ✨ includeタグの解析完了")

            # nodeタグの解析
            self._parse_nodes(root, launch_file=abs_launch_file)

        except ET.ParseError as e:
            print(f"❌ エラー: launchファイルの解析に失敗しました: {abs_launch_file}")
            print(f"   詳細: {str(e)}")

    def _parse_nodes(self, element: ET.Element, namespace: str = "",
                     launch_file: str = "") -> None:
        """ノード情報を抽出

        Args:
            element (ET.Element): XMLの要素
            namespace (str, optional): 名前空間. Defaults to "".
            launch_file (str, optional): launchファイルのパス. Defaults to None.
        """
        # nodeタグの処理
        for node in element.findall('.//node'):
            pkg = node.get('pkg')
            type_ = node.get('type')
            name = node.get('name')
            if name is None:
                continue
            if namespace and not name.startswith('/'):
                name = f"{namespace}/{name}"
            if pkg and type_:
                print(f"      ➕ ノード検出: {name} ({pkg}/{type_})")
                self.nodes[name] = {
                    'pkg': pkg,
                    'type': type_,
                    'launch_file': launch_file
                }

    def create_simple_graph(self, output_file: str) -> None:
        """シンプルな依存関係グラフを生成（launchファイル間の依存のみ）

        Args:
            output_file (str): 出力ファイル名（拡張子なし）
        """
        print("\n🎨 シンプルグラフの生成開始")
        dot = graphviz.Digraph(comment='ROS Launch Dependencies (Simple)')
        dot.attr(rankdir='LR')

        # グラフの属性設定
        dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
        dot.attr('edge', color='darkblue', fontcolor='darkblue')

        # ノードの作成（launchファイル名をノードとして扱う）
        created_nodes = set()  # 作成済みノードの追跡用

        # パッケージ名のマッピングを作成
        pkg_mapping = {}  # {launch_file_basename: package_name}
        for launch_file, includes in self.launch_dependencies.items():
            launch_base = os.path.basename(launch_file)
            for _, deps in self.launch_dependencies.items():
                for inc, pkg in deps:
                    inc_base = os.path.basename(inc)
                    if inc_base == launch_base and pkg:
                        pkg_mapping[launch_base] = pkg

        # まずlaunch_dependenciesからノードを作成
        for launch_file, includes in self.launch_dependencies.items():
            launch_base = os.path.basename(launch_file)
            if launch_base not in created_nodes:
                # パッケージ名を取得
                pkg_name = pkg_mapping.get(launch_base, "")

                label = launch_base
                if pkg_name:
                    label = f"{launch_base}\\n({pkg_name})"
                dot.node(launch_base, label)
                created_nodes.add(launch_base)
                print(f"   📦 ノード作成: {label}")

            for included, pkg_name in includes:
                included_base = os.path.basename(included)
                if included_base not in created_nodes:
                    # パッケージ名を取得（includesから得られない場合はマッピングから取得）
                    if not pkg_name:
                        pkg_name = pkg_mapping.get(included_base, "")

                    label = included_base
                    if pkg_name:
                        label = f"{included_base}\\n({pkg_name})"
                    dot.node(included_base, label)
                    created_nodes.add(included_base)
                    print(f"   📦 ノード作成: {label}")

        # launchファイル間の依存関係を追加
        print("\n🎯 依存関係の追加:")

        # 重複を防ぐために追加済みのエッジを記録
        added_edges = set()
        # ノードペアを記録（方向を無視）
        node_pairs = set()

        for launch_file, includes in self.launch_dependencies.items():
            launch_base = os.path.basename(launch_file)
            for included, _ in includes:
                included_base = os.path.basename(included)

                # エッジの識別子を作成
                edge_id = f"{launch_base}|{included_base}"

                # ノードペアを作成（ソートして方向を無視）
                node_pair = tuple(sorted([launch_base, included_base]))

                # 既に追加済みのエッジはスキップ
                if edge_id in added_edges:
                    print(f"   🔄 重複エッジをスキップ: {launch_base} -> {included_base}")
                    continue

                # 同じノードペア間に既にエッジがある場合はスキップ
                if node_pair in node_pairs:
                    print(f"   🔄 重複ノードペアをスキップ: {launch_base} <-> {included_base}")
                    continue

                print(f"   ➡️  {launch_base} -> {included_base}")
                dot.edge(launch_base, included_base, style='dashed', color='red')

                # 追加済みエッジとして記録
                added_edges.add(edge_id)
                # ノードペアを記録
                node_pairs.add(node_pair)

        # グラフの保存
        try:
            simple_output = f"{output_file}_simple"
            # dotファイルとPDFを生成
            dot.save(f"{simple_output}.dot")  # dotファイルを保存
            dot.render(simple_output, view=False, cleanup=True)  # PDFを生成（中間生成ファイルは削除）
            print("\n✅ シンプルグラフを生成しました:")
            print(f"   - DOT: {simple_output}.dot")
            print(f"   - PDF: {simple_output}.pdf")
        except Exception as e:
            print("\n❌ エラー: グラフの生成に失敗しました")
            print(f"   詳細: {str(e)}")

    def create_full_graph(self, output_file: str) -> None:
        """詳細なグラフを生成

        Args:
            output_file (str): 出力ファイル名（拡張子なし）
        """
        print("\n🎨 詳細グラフの生成開始")

        # CSVファイルの作成
        csv_file = f"{output_file}_nodes.csv"
        print(f"\n📝 CSVファイルの作成: {csv_file}")
        try:
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write("launch_file,node_name,package,type\n")
                for launch_file in self.launch_dependencies.keys():
                    launch_base = os.path.basename(launch_file)
                    nodes_in_file = [
                        (name, info) for name, info in self.nodes.items()
                        if info['launch_file'] == launch_file
                    ]
                    for node_name, info in nodes_in_file:
                        f.write(f"{launch_base},{node_name},{info['pkg']},{info['type']}\n")
            print(f"   ✅ CSVファイルを生成しました: {csv_file}")
        except Exception as e:
            print(f"   ❌ CSVファイルの生成に失敗しました: {str(e)}")

        print("\n📐 グラフ全体の設定:")
        dot = graphviz.Digraph(
            name='ros_nodes',
            filename=output_file,
            format='pdf',
            engine='dot',
            graph_attr={
                'rankdir': 'LR',      # 左から右へのレイアウト
                'newrank': 'true',    # 新しいランク制約を有効化
                'splines': 'curved',  # 曲線エッジに変更
                'concentrate': 'true',  # エッジの集約を有効化
                'compound': 'true',    # クラスタ間のエッジを許可
                'nodesep': '0.8',     # クラスタ間の間隔は広めに
                'ranksep': '0.8',     # ランク間の間隔
                'margin': '0',        # グラフ全体のマージン
                'pad': '0.3',         # グラフ全体のパディング
                'overlap': 'false',   # ノードの重なりを防ぐ
                'sep': '+15',         # ノード間の最小距離
                'esep': '+5'          # エッジ間の最小距離
            }
        )

        # ノードの基本設定
        dot.attr('node',
                 shape='box',
                 style='rounded,filled',
                 fillcolor='lightblue',
                 fixedsize='false',   # サイズを可変に変更
                 height='0.4',        # 高さを小さく
                 width='0.8',         # 幅を小さく
                 margin='0.1',        # マージンを小さく
                 fontsize='8'         # フォントサイズは小さいまま
                 )

        # エッジの基本設定
        dot.attr('edge',
                 style='dashed',     # 破線に変更
                 color='red',        # 赤色に変更
                 penwidth='0.5',     # 線を細く
                 arrowsize='0.3',    # 矢印を小さく
                 weight='0.1',       # エッジの重みを小さく
                 minlen='2'          # エッジの最小長を設定
                 )

        # クラスタ（サブグラフ）のマッピングを作成
        cluster_mapping = {}  # {launch_file: cluster_id}
        for launch_file in self.launch_dependencies.keys():
            cluster_id = self._generate_cluster_id(launch_file)
            cluster_mapping[launch_file] = cluster_id

        # クラスタ（サブグラフ）の作成
        for launch_file in self.launch_dependencies.keys():
            if launch_file not in cluster_mapping:
                continue

            cluster_id = cluster_mapping[launch_file]
            with dot.subgraph(name=f'cluster_{cluster_id}') as c:
                # クラスタの属性設定
                c.attr(
                    bgcolor='lightgrey',
                    color='gray70',
                    style='rounded',
                    penwidth='0.5',
                    margin='4',         # クラスタのマージンをさらに小さく
                    pad='0.2',          # クラスタのパディングをさらに小さく
                    fontsize='9',       # フォントサイズを調整
                    labeljust='l',
                    labelloc='t',
                    rank='same',        # 同じクラスタ内のノードを同じランクに
                    nodesep='0.1'       # クラスタ内のノード間隔を縮める
                )

                # ラベルの設定
                pkg_name = self._extract_package_name(launch_file)
                label = os.path.basename(launch_file)
                if pkg_name:
                    label = f"{label}\\n({pkg_name})"
                c.attr(label=label)

                # ダミーノードの追加（エッジ接続用）
                dummy_name = f"dummy_{cluster_id}"
                c.node(dummy_name,
                       label="",
                       shape='point',
                       width='0.1',
                       height='0.1',
                       style='invis'
                       )

                # ノードの追加
                nodes_in_file = [
                    (name, info) for name, info in self.nodes.items()
                    if info['launch_file'] == launch_file
                ]
                print(f"   📍 このファイルに含まれるノード数: {len(nodes_in_file)}")

                for node_name, info in nodes_in_file:
                    label = f"{node_name}\\n({info['pkg']}/{info['type']})"
                    print(f"      ➕ ノード追加: {node_name}")
                    print(f"         ラベル: {label}")
                    c.node(node_name, label, shape='box', style='rounded,filled',
                           fillcolor='white', margin='0.05', fontsize='8',
                           height='0.4', width='0.6', fixedsize='false')  # ノードのサイズを調整

        # 依存関係の追加
        print("\n🔗 依存関係の追加:")
        edge_count = 0

        # 重複を防ぐために追加済みのエッジを記録
        added_edges = set()
        # ノードペアを記録（方向を無視）
        node_pairs = set()

        # クラスタ間の依存関係を追加
        for launch_file, includes in self.launch_dependencies.items():
            if launch_file not in cluster_mapping:
                continue

            src_id = cluster_mapping[launch_file]
            src_cluster = f"cluster_{src_id}"
            src_dummy = f"dummy_{src_id}"

            for included, _ in includes:
                if included not in cluster_mapping:
                    continue

                dst_id = cluster_mapping[included]
                dst_cluster = f"cluster_{dst_id}"
                dst_dummy = f"dummy_{dst_id}"

                # エッジの識別子を作成
                edge_id = f"{src_cluster}|{dst_cluster}"

                # ノードペアを作成（ソートして方向を無視）
                node_pair = tuple(sorted([src_cluster, dst_cluster]))

                # 既に追加済みのエッジはスキップ
                if edge_id in added_edges:
                    print(f"   🔄 重複エッジをスキップ: {os.path.basename(launch_file)} ->"
                          f" {os.path.basename(included)}")
                    continue

                # 同じノードペア間に既にエッジがある場合はスキップ
                if node_pair in node_pairs:
                    print(f"   🔄 重複ノードペアをスキップ: {os.path.basename(launch_file)} <-> "
                          f"{os.path.basename(included)}")
                    continue

                edge_count += 1
                print(f"   ➡️  エッジ {edge_count}:")
                print(f"      - 始点: {os.path.basename(launch_file)}")
                print(f"      - 終点: {os.path.basename(included)}")

                dot.edge(src_dummy, dst_dummy,
                         ltail=src_cluster,
                         lhead=dst_cluster,
                         constraint='true',
                         minlen='2',         # エッジの最小長を増やす
                         weight='0.1',       # エッジの重みを小さく
                         dir='forward',
                         tailport='e',       # 始点を右端に
                         headport='w',       # 終点を左端に
                         style='dashed',     # 破線に変更
                         color='red'         # 赤色に変更
                         )

                # 追加済みエッジとして記録
                added_edges.add(edge_id)
                # ノードペアを記録
                node_pairs.add(node_pair)

        # ノード間のトピック依存関係を追加
        print("\n🔄 トピック依存関係の追加:")
        topic_edges = set()  # トピック依存関係の重複を防ぐ
        # ノードペアを記録（方向を無視）
        topic_node_pairs = set()

        for node_name, info in self.nodes.items():
            for pub in info.get('publishes', []):
                for sub_node, sub_info in self.nodes.items():
                    if node_name != sub_node and pub in sub_info.get('subscribes', []):
                        # エッジの識別子を作成
                        edge_id = f"{node_name}|{sub_node}|{pub}"

                        # ノードペアを作成（ソートして方向を無視）
                        node_pair = tuple(sorted([node_name, sub_node]))

                        # 既に追加済みのエッジはスキップ
                        if edge_id in topic_edges:
                            print(f"   🔄 重複トピックエッジをスキップ: {node_name} -> {sub_node} ({pub})")
                            continue

                        # 同じノードペア間に既にエッジがある場合はスキップ
                        if node_pair in topic_node_pairs:
                            print(f"   🔄 重複ノードペアをスキップ: {node_name} <-> {sub_node}")
                            continue

                        print(f"   ➡️  {node_name} -> {sub_node} ({pub})")
                        dot.edge(node_name, sub_node, label=pub, fontsize='8')
                        topic_edges.add(edge_id)
                        # ノードペアを記録
                        topic_node_pairs.add(node_pair)

        # グラフの保存
        print("\n💾 グラフの保存:")
        try:
            # dotファイルを生成
            dot.save(f"{output_file}.dot")
            print(f"   📄 DOTファイル生成: {output_file}.dot")

            # PDFを生成
            print(f"   📑 PDF生成開始: {output_file}.pdf")
            print("   🔧 レンダリング設定:")
            print("      - エンジン: dot")
            print("      - レンダラー: cairo")
            print("      - フォーマッタ: cairo")
            print("      - クリーンアップ: False")
            dot.render(output_file, view=False, cleanup=True)  # 中間生成ファイルは削除
            print("\n✅ グラフを生成しました:")
            print(f"   - DOT: {output_file}.dot")
            print(f"   - PDF: {output_file}.pdf")
        except Exception as e:
            print("\n❌ エラー: グラフの生成に失敗しました")
            print(f"   詳細: {str(e)}")

    def create_graph(self, output_file: str) -> None:
        """両方のグラフを生成

        Args:
            output_file (str): 出力ファイル名（拡張子なし）
        """
        self.create_simple_graph(output_file)
        self.create_full_graph(output_file)
