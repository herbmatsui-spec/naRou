from __future__ import annotations

from webgl_manager import WebGLManager


class DummyCanvas:
    def getContext(self, name: str):
        # Return a simple mock object identifying the context type
        return f"<MockWebGL2Context:{name}>"


def test_singleton_behavior():
    a = WebGLManager()
    b = WebGLManager()
    assert a is b, "WebGLManager should be a singleton"


def test_context_acquisition_and_caching():
    mgr = WebGLManager.instance()
    dummy = DummyCanvas()
    mgr.set_canvas(dummy)
    ctx1 = mgr.get_context()
    ctx2 = mgr.get_context()
    assert ctx1 == "<MockWebGL2Context:webgl2>"
    assert ctx1 is ctx2, "Subsequent get_context calls must return the same object"


def test_lazy_acquisition_when_canvas_set_later():
    mgr = WebGLManager.instance()
    # Reset internal state for isolated test
    mgr._canvas = None
    mgr._context = None
    # Assign canvas after manager creation
    dummy = DummyCanvas()
    mgr._canvas = dummy
    # The context should be created lazily on first get_context()
    ctx = mgr.get_context()
    assert ctx == "<MockWebGL2Context:webgl2>"
