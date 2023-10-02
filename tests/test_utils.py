import sys
from pathlib import Path
from unittest import TestCase

import pytest

from theflow import Compose
from theflow.utils.documentation import (
    get_compose_documentation,
    get_compose_documentation_from_module,
    get_composes_from_module,
)
from theflow.utils.hashes import naivehash
from theflow.utils.modules import (
    deserialize,
    import_dotted_string,
    init_object,
    serialize,
)
from theflow.utils.paths import is_name_matched, is_parent_of_child

from .assets.sample_flow import Func, Sum1


class TestNameMatching(TestCase):
    def test_name_matching_exact(self):
        """Test if the name matching is correct"""
        self.assertTrue(is_name_matched("", ""))
        self.assertTrue(is_name_matched(".main", ".main"))
        self.assertTrue(is_name_matched(".main.pipeline_A1", ".main.pipeline_A1"))
        self.assertFalse(is_name_matched(".main.pipeline_A1", ".main.pipeline_A2"))

    def test_name_matching_wildcard(self):
        """Test for wildcard matching"""
        self.assertTrue(
            is_name_matched(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_a",
                ".main.*.pipeline_B2.*.step_a",
            )
        )

        self.assertTrue(
            is_name_matched(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_a",
                ".main.*.pipeline_B2.pipeline*.step_a",
            )
        )

        self.assertFalse(
            is_name_matched(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_a.some_step",
                ".main.*.pipeline_B2.pipeline*.step_a",
            )
        )


class TestParentChildMatching(TestCase):
    def test_parent_child_matching_exact(self):
        """Test if the parent-child matching is correct"""
        self.assertTrue(
            is_parent_of_child(".main.pipeline_A1", ".main.pipeline_A1.pipeline_B1")
        )

        self.assertFalse(is_parent_of_child(".main.pipeline_A1", ".main.pipeline_A2"))

    def test_parent_child_matching_wildcard(self):
        """Test for wildcard matching"""
        self.assertTrue(
            is_parent_of_child(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2",
                ".main.*.pipeline_B2.*.step_a",
            )
        )

        self.assertTrue(
            is_parent_of_child(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2",
                ".main.*.pipeline_B2.pipeline*.step_a",
            )
        )

        self.assertFalse(
            is_parent_of_child(
                ".main.pipeline_A1.pipeline_B2.pipeline_C2",
                ".main.*.pipeline_B2.pipeline*.step_a.some_step",
            )
        )


class TestImportDottedString(TestCase):
    def test_import_class(self):
        """Test it can import class"""
        from pathlib import Path

        self.assertEqual(import_dotted_string("pathlib.Path", safe=False), Path)

    def test_import_function(self):
        """Test it can import function"""
        self.assertEqual(
            import_dotted_string(
                "theflow.utils.modules.import_dotted_string", safe=False
            ),
            import_dotted_string,
        )

    def test_import_safe_no_allowed_modules_raise_error(self):
        """Test that safe import without modules will raise error"""
        with self.assertRaises(ValueError):
            import_dotted_string("pathlib.Path")

    def test_import_safe_missing_allowed_modules_raise_error(self):
        """Test that safe import with missing modules will raise error"""
        import re

        with self.assertRaises(ValueError):
            import_dotted_string("pathlib.Path", allowed_modules={"re": re})

    def test_import_safe_with_allowed_modules(self):
        """Test that safe import with allowed modules will not raise error"""
        import re
        from pathlib import Path

        self.assertEqual(
            import_dotted_string(
                "pathlib.Path", allowed_modules={"pathlib.Path": Path, "re": re}
            ),
            Path,
        )


class TestInitObject(TestCase):
    def test_construct_with_params_unsafe(self):
        """Can construct with params"""
        from datetime import datetime

        obj_dict = {"__type__": "datetime.datetime", "year": 2020, "month": 1, "day": 1}
        obj = init_object(obj_dict, safe=False)
        self.assertEqual(obj, datetime(2020, 1, 1))

    def test_raise_by_default(self):
        """Raise by default since this method involve code execution"""
        obj_dict = {"__type__": "datetime.datetime", "year": 2020, "month": 1, "day": 1}
        with self.assertRaises(ValueError):
            init_object(obj_dict)

    def test_raise_missing_modules(self):
        """Raise if missing modules"""
        from pathlib import Path

        obj_dict = {"__type__": "datetime.datetime", "year": 2020, "month": 1, "day": 1}
        with self.assertRaises(ValueError):
            init_object(obj_dict, allowed_modules={"pathlib.Path": Path})

    def test_construct_with_params_safe(self):
        """Normal behavior: construct with params in a safe manner"""
        from datetime import datetime

        obj_dict = {"__type__": "datetime.datetime", "year": 2020, "month": 1, "day": 1}
        obj = init_object(obj_dict, allowed_modules={"datetime.datetime": datetime})
        self.assertEqual(obj, datetime(2020, 1, 1))

    def test_construct_without_params(self):
        """Init object without params"""
        from pathlib import Path

        obj_dict = {"__type__": "pathlib.Path"}
        obj = init_object(obj_dict, allowed_modules={"pathlib.Path": Path})
        self.assertEqual(obj, Path())

    def test_raise_without_type(self):
        """Raise if __type__ is not specified"""
        obj_dict = {"year": 2020, "month": 1, "day": 1}
        with self.assertRaises(ValueError):
            init_object(obj_dict, safe=False)


class TestSerialize(TestCase):
    def test_serialize_simple_builtin_types(self):
        """Simple built-in types will be returned as is"""
        self.assertEqual(serialize(0.5), 0.5)
        self.assertEqual(serialize(None), None)
        self.assertEqual(serialize(True), True)
        self.assertEqual(serialize(1), 1)
        self.assertEqual(serialize("1"), "1")
        self.assertEqual(serialize([1, 2, 3]), [1, 2, 3])
        self.assertEqual(serialize((1, 2, 3)), (1, 2, 3))
        self.assertEqual(serialize({"a": 1, "b": 2}), {"a": 1, "b": 2})

    def test_serialize_complex_python_object(self):
        """Complex objects should become dotted string wrapped by double curly braces"""
        from pathlib import Path

        self.assertEqual(serialize(Path), "{{ pathlib.Path }}")
        self.assertEqual(serialize(serialize), "{{ theflow.utils.modules.serialize }}")

    def test_serialize_composite_list(self):
        """Composite type should be serialized as dotted string wrapped by double
        curly braces
        """
        from pathlib import Path

        from theflow.base import Compose

        self.assertEqual(serialize([Compose, 6]), ["{{ theflow.base.Compose }}", 6])
        self.assertEqual(
            serialize([Compose, 6, [Path, "hello"]]),
            ["{{ theflow.base.Compose }}", 6, ["{{ pathlib.Path }}", "hello"]],
        )

    def test_serialize_composite_dict(self):
        """Composite type should be serialized as dotted string wrapped by double
        curly braces
        """
        from pathlib import Path

        from theflow.base import Compose

        self.assertEqual(
            serialize({"a": Compose, "b": 6}),
            {"a": "{{ theflow.base.Compose }}", "b": 6},
        )
        self.assertEqual(
            serialize({"a": Compose, "b": 6, "c": {"hello": Path}}),
            {
                "a": "{{ theflow.base.Compose }}",
                "b": 6,
                "c": {"hello": "{{ pathlib.Path }}"},
            },
        )

    @pytest.mark.skip(reason="TODO: not work yet")
    def test_serialize_type_annotation(self):
        """Type will be serialized mostly as is, except object will be dotted string"""
        from typing import Any, Union

        self.assertEqual(serialize(Any), "{{ typing.Any }}")
        self.assertEqual(serialize(Union[str, int]), "{{ typing.Union[str, int] }}")
        self.assertEqual(serialize(list[Compose]), "{{ list[theflow.base.Compose] }}")


class TestDeserialize(TestCase):
    def test_deserialize_simple_builtin_types(self):
        """Simple built-in types will be returned as is"""
        self.assertEqual(deserialize(0.5), 0.5)
        self.assertEqual(deserialize(None), None)
        self.assertEqual(deserialize(True), True)
        self.assertEqual(deserialize(1), 1)
        self.assertEqual(deserialize("1"), "1")
        self.assertEqual(deserialize([1, 2, 3]), [1, 2, 3])
        self.assertEqual(deserialize((1, 2, 3)), (1, 2, 3))
        self.assertEqual(deserialize({"a": 1, "b": 2}), {"a": 1, "b": 2})

    def test_deserialize_complex_python_object_unsafe(self):
        """Complex Python object with dotted string will be imported"""
        from pathlib import Path

        self.assertEqual(deserialize("{{ pathlib.Path }}", safe=False), Path)
        self.assertEqual(
            deserialize("{{ theflow.utils.modules.serialize }}", safe=False), serialize
        )

    def test_deserialize_composite_list_unsafe(self):
        """Complex Python object within list"""
        from pathlib import Path

        from theflow.base import Compose

        self.assertEqual(
            deserialize(["{{ theflow.base.Compose }}", 6], safe=False),
            [Compose, 6],
        )
        self.assertEqual(
            deserialize(
                ["{{ theflow.base.Compose }}", 6, ["{{ pathlib.Path }}", "hello"]],
                safe=False,
            ),
            [Compose, 6, [Path, "hello"]],
        )

    def test_deserialize_composite_dict_unsafe(self):
        """Composite type should be serialized as dotted string wrapped by double
        curly braces
        """
        from pathlib import Path

        from theflow.base import Compose

        self.assertEqual(
            deserialize({"a": "{{ theflow.base.Compose }}", "b": 6}, safe=False),
            {"a": Compose, "b": 6},
        )
        self.assertEqual(
            deserialize(
                {
                    "a": "{{ theflow.base.Compose }}",
                    "b": 6,
                    "c": {"hello": "{{ pathlib.Path }}"},
                },
                safe=False,
            ),
            {"a": Compose, "b": 6, "c": {"hello": Path}},
        )

    @pytest.mark.skip(reason="TODO: not work yet")
    def test_serialize_type_annotation(self):
        """Type will be serialized mostly as is, except object will be dotted string"""
        from typing import Any, Union

        self.assertEqual(serialize(Any), "{{ typing.Any }}")
        self.assertEqual(serialize(Union[str, int]), "{{ typing.Union[str, int] }}")
        self.assertEqual(serialize(list[Compose]), "{{ list[theflow.base.Compose] }}")


class TestDocumentationUtility(TestCase):
    def test_get_compose_documentation(self):
        """Test get compose full information: docstring, ndoes, params"""
        sum1_doc = get_compose_documentation(Sum1)
        assert sum1_doc["desc"] == ""
        assert sum1_doc["nodes"] == {}

        plus_doc = get_compose_documentation(Func)
        assert plus_doc["desc"] == "Function calculation"
        assert plus_doc["params"]["a"]["desc"] == "The `a` number"
        assert plus_doc["params"]["a"]["default"] == 100
        assert plus_doc["params"]["e"]["desc"] == "The `e` number"
        assert plus_doc["nodes"]["y"]["desc"] == "The `y` node"
        assert plus_doc["nodes"]["z"]["depends_on"] == ["x"]

    def test_get_composes_from_module(self):
        """Test getting all compose from module"""
        sys.path.append(str(Path(__file__).parent))
        composes = get_composes_from_module("assets.sample_flow")
        assert len(composes) == 4

    def test_get_all_compose_documentation_from_module(self):
        sys.path.append(str(Path(__file__).parent))
        definition = get_compose_documentation_from_module("assets.sample_flow")
        assert len(definition) == 4


class A:
    a = 10
    y = 11

    def __init__(self, a, b):
        self.a = a
        self.b = b


class B:
    a = 10
    y = 11

    def __init__(self, a, b):
        self.a = a
        self.b = b


class TestNaiveHash(TestCase):
    to_check = [
        0,
        1,
        1.0,
        True,
        False,
        None,
        "hello",
        "1",
        [],
        [1],
        [1, 2],
        [2, 1],
        {},
        {1: 2},
        {"1": 2},
        {(1, 2): A(1, 2)},
        set(),
        {1, 2},
        {2, 1},
        {"1", "2"},
        A,
        B,
        A(1, 2),
        B(1, 2),
    ]

    def test_hash_scalar_type(self):
        """Test work with int, float, bool, string"""
        self.assertEqual(naivehash()(0), "d6c6d6b1491707dc57506e7dfb7cccba")
        self.assertEqual(naivehash()(1), "67af089a4426724964d7927610a9c42f")
        self.assertEqual(naivehash()(1.0), "66d5a3a7b42af4fadff4e4a8786be2cd")
        self.assertEqual(naivehash()(True), "4d81551eb15eacaed010de3a792efad4")
        self.assertEqual(naivehash()(False), "5e7c9fef3bfb150080ba7884ab0e20a3")
        self.assertEqual(naivehash()(None), "825f629c731075490e37c1f220781b68")
        self.assertEqual(naivehash()("hello"), "006892b196dd42e56ae296d46ba796f9")
        self.assertEqual(naivehash()("1"), "751d4a188f5eeb3ad70989aefad475a3")

    def test_hash_list_tuple_dict_set_type(self):
        self.assertEqual(naivehash()([]), "61699d460f9e05f95aae56e73b86e742")
        self.assertEqual(naivehash()([1]), "5cc551296cd2d79ad6ace14e7bac72c4")
        self.assertEqual(naivehash()([1, 2]), "cc0f2d78211dcda8bfd4ef80930c7982")
        self.assertEqual(naivehash()([]), "61699d460f9e05f95aae56e73b86e742")
        self.assertEqual(naivehash()([1]), "5cc551296cd2d79ad6ace14e7bac72c4")
        self.assertEqual(naivehash()([1, 2]), "cc0f2d78211dcda8bfd4ef80930c7982")
        self.assertEqual(naivehash()([2, 1]), "1c2bf5865c9df59d93bbcbe538b8663b")
        self.assertEqual(naivehash()({}), "03f7e77c0cba63ae7a9c75ccfbfe33e0")
        self.assertEqual(naivehash()({1: 2}), "b797b7645bcef16d8fce546ca5d1dc03")
        self.assertEqual(naivehash()({"1": 2}), "7296fb42d9464d15a65e71f671b2e480")
        self.assertEqual(
            naivehash()({(1, 2): A(1, 2)}), "4aa5f2bc684976b1d4bfa42dda8d2834"
        )
        self.assertEqual(naivehash()(set()), "9ce70b11fda866035eb013c8de5b8692")
        self.assertEqual(naivehash()({1, 2}), "84a6c62c58e7728fde564a8e3d295668")
        self.assertEqual(naivehash()({2, 1}), "84a6c62c58e7728fde564a8e3d295668")
        self.assertEqual(naivehash()({"1", "2"}), "26005d20f5d6a994175dc966c7892fae")

    def test_hash_python_cls(self):
        self.assertEqual(naivehash()(A), "70b407430beecc9bc74c1a5bc4fc1c96")
        self.assertEqual(naivehash()(B), "660295ea053da2539041edc18bf54a3b")

    def test_hash_python_instance(self):
        self.assertEqual(naivehash()(A(1, 2)), "8ab6e307217edbc9e6df487b12780903")
        self.assertEqual(naivehash()(B(1, 2)), "3ea105db0fac432569deb2ea74eea8e5")
