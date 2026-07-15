# Fortvna 唯一命令入口 (第 4.2 条)
# 用法: just setup / test / lint / typecheck / up / down / doctor

default:
    @just --list

# 一次性: 同步依赖 + 安装 pre-commit 钩子
setup:
    uv sync --all-packages
    uv run pre-commit install
    @echo "✅ setup 完成. 记得: direnv allow"

# 全部质量门禁 (CI 等价)
check: lint typecheck test secrets-scan

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff format .
    uv run ruff check --fix .

typecheck:
    uv run mypy factor_zoo cosmos minisha

test:
    uv run pytest -q

secrets-scan:
    gitleaks detect --no-banner --verbose

# 启动/停止本地基础设施 (postgres, redis)
up:
    docker compose up -d

down:
    docker compose down

# 环境自检: 工具链 + 密钥文件权限 (第 5.3 条)
doctor:
    @command -v uv >/dev/null && echo "✅ uv" || echo "❌ uv 缺失"
    @command -v direnv >/dev/null && echo "✅ direnv" || echo "❌ direnv 缺失"
    @command -v gitleaks >/dev/null && echo "✅ gitleaks" || echo "❌ gitleaks 缺失"
    @command -v docker >/dev/null && echo "✅ docker" || echo "❌ 容器运行时缺失 (brew install --cask orbstack)"
    @test -f ~/.fortvna/secrets.env && echo "✅ secrets.env 存在" || echo "❌ ~/.fortvna/secrets.env 缺失"
    @test "$(stat -f '%A' ~/.fortvna/secrets.env 2>/dev/null)" = "600" && echo "✅ secrets.env 权限 600" || echo "❌ secrets.env 权限非 600 —— 执行: chmod 600 ~/.fortvna/secrets.env"
