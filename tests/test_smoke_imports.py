def test_core_modules_import_without_freecad():
    # These imports should work in plain CPython without FreeCAD installed.
    import freecad_gitpdm.core.log  # noqa: F401
    import freecad_gitpdm.core.settings  # noqa: F401
    import freecad_gitpdm.core.publish  # noqa: F401


def test_git_modules_import_without_freecad():
    import freecad_gitpdm.git.client  # noqa: F401


def test_github_modules_import_without_freecad():
    import freecad_gitpdm.github.errors  # noqa: F401
    import freecad_gitpdm.github.api_client  # noqa: F401
    import freecad_gitpdm.github.identity  # noqa: F401


def test_oauth_modules_import_without_freecad():
    import freecad_gitpdm.auth.oauth_device_flow  # noqa: F401
    import freecad_gitpdm.auth.token_store  # noqa: F401


def test_export_modules_import_without_freecad():
    import freecad_gitpdm.export.stl_converter  # noqa: F401
    import freecad_gitpdm.export.exporter  # noqa: F401
