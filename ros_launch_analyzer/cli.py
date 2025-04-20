#!/usr/bin/env python3
"""
ROSのlaunchファイル解析ツールのコマンドラインインターフェース

SPDX-License-Identifier: MIT
(C) 2025 Daisuke Sato
"""

import argparse
import os
import sys

from .analyzer import LaunchAnalyzer


def main() -> int:
    """コマンドラインエントリーポイント"""
    parser = argparse.ArgumentParser(description='ROSのlaunchファイルを解析し、依存関係グラフを生成します')
    parser.add_argument('launch_file', help='解析するlaunchファイルのパス')
    parser.add_argument('--ros-ws', dest='ros_ws', default='',
                        help='ROSワークスペースのパス（省略可）')
    parser.add_argument('--output', '-o', dest='output', default='ros_nodes_graph',
                        help='出力ファイル名（拡張子なし）')
    parser.add_argument('--simple-only', dest='simple_only', action='store_true',
                        help='シンプルグラフのみ生成')
    parser.add_argument('--full-only', dest='full_only', action='store_true',
                        help='詳細グラフのみ生成')

    args = parser.parse_args()

    # 入力ファイルの存在確認
    if not os.path.exists(args.launch_file):
        print(f"エラー: 指定されたlaunchファイルが見つかりません: {args.launch_file}")
        sys.exit(1)

    # 解析実行
    analyzer = LaunchAnalyzer(os.path.dirname(args.launch_file), args.ros_ws)

    if os.path.isfile(args.launch_file):
        # 単一のファイルを解析
        if args.launch_file.endswith('.launch'):
            analyzer.parse_launch_file(args.launch_file)
        else:
            print(f"❌ エラー: 指定されたファイルはlaunchファイルではありません: {args.launch_file}")
            return 1
    else:
        # ディレクトリ内のすべてのlaunchファイルを解析
        for root, _, files in os.walk(args.launch_file):
            for file in files:
                if file.endswith('.launch'):
                    launch_file = os.path.join(root, file)
                    analyzer.parse_launch_file(launch_file)

    # 単一ファイルの場合は、そのファイルに関連するノードのみを含むグラフを生成
    if os.path.isfile(args.launch_file):
        target_file = os.path.abspath(args.launch_file)
        # 関連するファイルのみを抽出
        related_files = {target_file}
        for launch_file, includes in analyzer.launch_dependencies.items():
            if launch_file == target_file:
                related_files.update(inc for inc, _ in includes)
            else:
                for inc, _ in includes:
                    if inc == target_file:
                        related_files.add(launch_file)
                        related_files.add(inc)

        # 関連しないファイルを削除
        analyzer.launch_dependencies = {
            k: [(f, p) for f, p in v if f in related_files]
            for k, v in analyzer.launch_dependencies.items()
            if k in related_files
        }

        # 関連しないノードを削除
        analyzer.nodes = {
            name: info for name, info in analyzer.nodes.items()
            if info['launch_file'] in related_files
        }

    # グラフ生成
    if args.simple_only:
        analyzer.create_simple_graph(args.output)
    elif args.full_only:
        analyzer.create_full_graph(args.output)
    else:
        analyzer.create_graph(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
