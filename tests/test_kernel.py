"""Unit tests for the Kernel package/dependency system."""
from __future__ import annotations

import pytest

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


class _FakePackage(IPackage):
    def __init__(self, name, deps=None, requires=None, on_load=None, setup=None):
        self._meta = PackageMetadata(name=name, dependencies=deps or [], requires=requires or [])
        self._on_load = on_load
        self._setup = setup

    @property
    def metadata(self):
        return self._meta

    def on_load(self, kernel):
        if self._on_load:
            self._on_load(kernel)

    def setup(self, kernel):
        if self._setup:
            self._setup(kernel)

    def teardown(self, kernel):
        pass


def test_register_and_get_system():
    k = Kernel()
    k.register_system("thing", 123)
    assert k.get_system("thing") == 123
    assert k.has_system("thing")


def test_get_system_default_overload():
    k = Kernel()
    assert k.get_system("missing", "none") == "none"


def test_get_system_strict_raises():
    k = Kernel()
    with pytest.raises(KeyError):
        k.get_system_strict("missing")


def test_load_package_order():
    k = Kernel()
    loaded: list[str] = []

    def make(name):
        return _FakePackage(name, on_load=lambda k: loaded.append(name))

    k.load_package(make("core"))
    k.load_package(make("world"))
    assert loaded == ["core", "world"]
    assert k.get_package("core") is not None


def test_missing_dependency_raises():
    k = Kernel()
    with pytest.raises(RuntimeError):
        k.load_package(_FakePackage("child", deps=["missing"]))
