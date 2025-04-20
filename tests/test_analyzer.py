import sys
from pathlib import Path
import pytest
from typing import Iterator

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ros_launch_analyzer.analyzer import LaunchAnalyzer  # noqa: E402

# テストデータディレクトリのパス
TEST_DATA_DIR = Path(__file__).parent / "test_data"
FAKE_WS_DIR = TEST_DATA_DIR / "fake_ros_ws"
PKG_A_LAUNCH_DIR = FAKE_WS_DIR / "src" / "pkg_a" / "launch"
PKG_B_LAUNCH_DIR = FAKE_WS_DIR / "src" / "pkg_b" / "launch"


# フィクスチャは残すが中身は空にする (将来的な拡張用)
@pytest.fixture(scope="module")
def setup_test_environment() -> Iterator[None]:
    """テスト環境のセットアップ（現状は特に何もしない）"""
    print("DEBUG: Running setup_test_environment fixture (now empty)")
    yield  # テスト実行
    print("DEBUG: Running teardown for setup_test_environment fixture (now empty)")
    # クリーンアップ処理も不要


@pytest.fixture
def analyzer() -> LaunchAnalyzer:
    """テスト用のLaunchAnalyzerインスタンスを作成"""
    return LaunchAnalyzer(launch_dir=str(TEST_DATA_DIR), ros_ws_dir=str(FAKE_WS_DIR))


def test_init(analyzer: LaunchAnalyzer) -> None:
    """LaunchAnalyzerの初期化テスト"""
    assert analyzer.launch_dir == str(TEST_DATA_DIR.resolve())
    assert analyzer.ros_ws_dir == str(FAKE_WS_DIR.resolve())
    assert isinstance(analyzer.launch_dependencies, dict)
    assert isinstance(analyzer.nodes, dict)


def test_find_package_path(analyzer: LaunchAnalyzer) -> None:
    """_find_package_path のテスト"""
    pkg_a_path = analyzer._find_package_path("pkg_a")
    assert pkg_a_path == str((FAKE_WS_DIR / "src" / "pkg_a").resolve())
    pkg_b_path = analyzer._find_package_path("pkg_b")
    assert pkg_b_path == str((FAKE_WS_DIR / "src" / "pkg_b").resolve())
    # キャッシュのテスト
    assert "pkg_a" in analyzer.pkg_path_cache
    assert analyzer.pkg_path_cache["pkg_a"] == pkg_a_path
    # 存在しないパッケージ
    non_exist_path = analyzer._find_package_path("non_existent_pkg")
    assert non_exist_path == ""


def test_resolve_find_expression(analyzer: LaunchAnalyzer) -> None:
    """_resolve_find_expression のテスト"""
    text_find_a = "$(find pkg_a)/launch/a.launch"
    pkg_a_resolved = str((FAKE_WS_DIR / 'src' / 'pkg_a').resolve())
    expected_find_a = f"{pkg_a_resolved}/launch/a.launch"
    assert analyzer._resolve_find_expression(text_find_a) == expected_find_a

    text_no_find = "path/to/file.launch"
    assert analyzer._resolve_find_expression(text_no_find) == text_no_find

    text_multi = "$(find pkg_a)/ A $(find pkg_b)/B"
    pkg_b_resolved = str((FAKE_WS_DIR / 'src' / 'pkg_b').resolve())
    expected_multi = f"{pkg_a_resolved}/ A {pkg_b_resolved}/B"
    assert analyzer._resolve_find_expression(text_multi) == expected_multi

    text_not_found = "$(find non_existent)/file"
    assert analyzer._resolve_find_expression(text_not_found) == text_not_found


def test_parse_simple_launch(analyzer: LaunchAnalyzer, setup_test_environment: None) -> None:
    """単純なlaunchファイルの解析テスト"""
    launch_file = TEST_DATA_DIR / "simple.launch"
    analyzer.parse_launch_file(str(launch_file))

    abs_path = str(launch_file.resolve())
    assert abs_path in analyzer.launch_dependencies
    assert not analyzer.launch_dependencies[abs_path]  # includeなし
    assert "simple_node" in analyzer.nodes
    assert analyzer.nodes["simple_node"]["pkg"] == "pkg_simple"
    assert analyzer.nodes["simple_node"]["type"] == "type_simple"
    assert analyzer.nodes["simple_node"]["launch_file"] == abs_path


def test_parse_include_find(analyzer: LaunchAnalyzer, setup_test_environment: None) -> None:
    """$(find) を含むincludeの解析テスト"""
    launch_file = TEST_DATA_DIR / "include_find.launch"
    analyzer.parse_launch_file(str(launch_file))

    abs_path = str(launch_file.resolve())
    included_path = str((PKG_A_LAUNCH_DIR / "a_node.launch").resolve())

    assert abs_path in analyzer.launch_dependencies
    # 依存関係のチェック
    assert len(analyzer.launch_dependencies[abs_path]) == 1
    dep_path, dep_pkg = analyzer.launch_dependencies[abs_path][0]
    assert dep_path == included_path
    assert dep_pkg == "pkg_a"

    # includeされたファイルも解析されているか
    assert included_path in analyzer.launch_dependencies

    # ノードのチェック
    assert "finder_node" in analyzer.nodes
    assert analyzer.nodes["finder_node"]["launch_file"] == abs_path
    assert "node_a" in analyzer.nodes
    assert analyzer.nodes["node_a"]["launch_file"] == included_path


def test_parse_include_two_levels(analyzer: LaunchAnalyzer, setup_test_environment: None) -> None:
    """2階層の $(find) include を含む launch ファイルの解析テスト"""
    # grandparent.launch を解析対象とする
    # LaunchAnalyzer の launch_dir は pkg_a/launch を指すように変更
    analyzer.launch_dir = str(PKG_A_LAUNCH_DIR.resolve())
    launch_file = PKG_A_LAUNCH_DIR / "grandparent.launch"
    analyzer.parse_launch_file(str(launch_file))

    # ファイルの絶対パスを取得
    gp_path = str(launch_file.resolve())
    parent_path = str((PKG_A_LAUNCH_DIR / "parent.launch").resolve())
    child_path = str((PKG_B_LAUNCH_DIR / "child.launch").resolve())

    # 依存関係のチェック
    # grandparent -> parent
    assert gp_path in analyzer.launch_dependencies
    assert len(analyzer.launch_dependencies[gp_path]) == 1
    dep_path_gp, dep_pkg_gp = analyzer.launch_dependencies[gp_path][0]
    assert dep_path_gp == parent_path
    assert dep_pkg_gp == "pkg_a"

    # parent -> child
    assert parent_path in analyzer.launch_dependencies
    assert len(analyzer.launch_dependencies[parent_path]) == 1
    dep_path_p, dep_pkg_p = analyzer.launch_dependencies[parent_path][0]
    assert dep_path_p == child_path
    assert dep_pkg_p == "pkg_b"

    # child には依存関係がない
    assert child_path in analyzer.launch_dependencies
    assert not analyzer.launch_dependencies[child_path]

    # ノードのチェック
    assert "grandparent_node" in analyzer.nodes
    assert analyzer.nodes["grandparent_node"]["launch_file"] == gp_path

    assert "parent_node" in analyzer.nodes
    assert analyzer.nodes["parent_node"]["launch_file"] == parent_path

    assert "child_node" in analyzer.nodes
    assert analyzer.nodes["child_node"]["launch_file"] == child_path
