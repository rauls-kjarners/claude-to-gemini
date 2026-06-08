import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["lint", "type_check", "tests"]


def install_deps(session: nox.Session) -> None:
    """Sync the dev dependency group into this session's venv.

    UV_PROJECT_ENVIRONMENT points uv at nox's per-session venv instead of
    the project's default .venv, so each matrix interpreter is isolated.
    """
    session.run_install(
        "uv",
        "sync",
        "--group",
        "dev",
        external=True,
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )


@nox.session(python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def tests(session: nox.Session) -> None:
    """Run the test suite across all supported Python versions."""
    install_deps(session)
    session.run("pytest", *session.posargs)


@nox.session(python="3.14")
def lint(session: nox.Session) -> None:
    """Run linting and formatting checks."""
    install_deps(session)
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session(python="3.14")
def type_check(session: nox.Session) -> None:
    """Run strict type checking."""
    install_deps(session)
    session.run("pyright")
