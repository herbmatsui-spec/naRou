from webgl_resource_pool import WebGLResourcePool


# Simple creator that returns a new dict identifying the resource
def make_shader(name):
    return {"type": "shader", "name": name}


def test_acquire_creates_and_caches_resource():
    pool = WebGLResourcePool()
    shader_a = pool.acquire("shader", "basic", lambda: make_shader("basic"))
    shader_b = pool.acquire("shader", "basic", lambda: make_shader("basic"))
    assert shader_a is shader_b, (
        "Repeated acquire with same key must return cached object"
    )
    assert shader_a["name"] == "basic"


def test_release_removes_resource():
    pool = WebGLResourcePool()
    shader = pool.acquire("shader", "temp", lambda: make_shader("temp"))
    pool.release("shader", "temp")
    # After release, a new acquire should produce a different object
    new_shader = pool.acquire("shader", "temp", lambda: make_shader("temp"))
    assert new_shader is not shader


def test_clear_empties_pool():
    pool = WebGLResourcePool()
    pool.acquire("shader", "a", lambda: make_shader("a"))
    pool.acquire("buffer", "b", lambda: {"type": "buffer", "id": 1})
    assert len(pool.keys()) == 2
    pool.clear()
    assert pool.keys() == []
