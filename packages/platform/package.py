from __future__ import annotations

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


# Module-level function for pickling support
def _create_web_server(engine, port=8080):
    from web_server import start_web_server

    return start_web_server(engine, port=port)


class PlatformPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="platform",
            provides=[
                "web_server_factory",
                "cli_renderer",
                "input_handler",
            ],
            requires=["renderer", "event_bus"],
            dependencies=["core"],
        )

    def setup(self, kernel: Kernel) -> None:
        from input_handler import InputHandler

        kernel.register_system("web_server_factory", _create_web_server)
        kernel.register_system("input_handler", InputHandler())
        # CLI renderer uses existing renderer

    def teardown(self, kernel: Kernel) -> None:
        pass
