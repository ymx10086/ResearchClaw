from pathlib import Path

from researchclaw.providers.store import ProviderStore


def test_provider_store_save_list_remove(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "openai-main",
            "provider_type": "openai",
            "model_name": "gpt-4o",
            "model_names": ["gpt-4o"],
            "api_key": "sk-test",
            "base_url": "",
            "extra": {},
        },
    )

    items = store.list_providers()
    assert len(items) == 1
    assert items[0]["name"] == "openai-main"

    store.remove_provider("openai-main")
    assert store.list_providers() == []


def test_provider_store_ollama_base_url_normalized(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))
    store.save_provider(
        {
            "name": "ollama-local",
            "provider_type": "ollama",
            "model_name": "llama3",
            "model_names": ["llama3"],
            "api_key": "",
            "base_url": "http://localhost:11434",
            "extra": {},
        },
    )
    item = store.get_provider("ollama-local")
    assert item is not None
    assert item.base_url == "http://localhost:11434/v1"


def test_provider_store_set_enabled_is_exclusive(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))
    store.save_provider({"name": "a", "provider_type": "openai"})
    store.save_provider({"name": "b", "provider_type": "anthropic"})

    store.set_enabled("a")
    assert store.get_provider("a").enabled is True
    assert store.get_provider("b").enabled is False

    store.set_enabled("b")
    assert store.get_provider("a").enabled is False
    assert store.get_provider("b").enabled is True


def test_provider_store_auto_enables_first_provider_when_unspecified(
    tmp_path: Path,
):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "gemini-main",
            "provider_type": "gemini",
            "model_name": "gemini-2.5-flash",
            "api_key": "AIza-demo",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        },
    )

    item = store.get_provider("gemini-main")
    assert item is not None
    assert item.enabled is True
    assert store.get_active_provider() is not None
    assert store.get_active_provider().name == "gemini-main"


def test_provider_store_respects_explicit_disabled_first_provider(
    tmp_path: Path,
):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "gemini-main",
            "provider_type": "gemini",
            "model_name": "gemini-2.5-flash",
            "api_key": "AIza-demo",
            "enabled": False,
        },
    )

    item = store.get_provider("gemini-main")
    assert item is not None
    assert item.enabled is False
    assert store.get_active_provider() is None


def test_provider_store_re_save_without_active_auto_repairs_provider(
    tmp_path: Path,
):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "gemini-main",
            "provider_type": "gemini",
            "model_name": "gemini-2.5-flash",
            "api_key": "AIza-demo",
            "enabled": False,
        },
    )

    store.save_provider(
        {
            "name": "gemini-main",
            "provider_type": "gemini",
            "model_name": "gemini-2.5-pro",
            "api_key": "AIza-demo",
        },
    )

    item = store.get_provider("gemini-main")
    assert item is not None
    assert item.enabled is True
    assert item.model_name == "gemini-2.5-pro"


def test_provider_store_multiple_models_round_trip(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "openrouter-main",
            "provider_type": "openai",
            "model_names": ["openai/gpt-5.1", "anthropic/claude-sonnet-4"],
            "api_key": "sk-test",
            "base_url": "https://openrouter.ai/api/v1",
            "extra": {},
        },
    )

    item = store.get_provider("openrouter-main")
    assert item is not None
    assert item.model_name == "openai/gpt-5.1"
    assert item.model_names == ["openai/gpt-5.1", "anthropic/claude-sonnet-4"]


def test_provider_store_legacy_single_model_populates_model_names(
    tmp_path: Path,
):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "legacy-openai",
            "provider_type": "openai",
            "model_name": "gpt-4o",
            "api_key": "sk-test",
        },
    )

    item = store.get_provider("legacy-openai")
    assert item is not None
    assert item.model_name == "gpt-4o"
    assert item.model_names == ["gpt-4o"]


def test_provider_store_accepts_minimax_provider_type(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "minimax-main",
            "provider_type": "minimax",
            "model_name": "MiniMax-M2.7",
            "api_key": "sk-test",
            "base_url": "https://api.minimax.io/v1",
        },
    )

    item = store.get_provider("minimax-main")
    assert item is not None
    assert item.provider_type == "minimax"
    assert item.model_name == "MiniMax-M2.7"


def test_provider_store_accepts_gemini_provider_type(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "gemini-main",
            "provider_type": "gemini",
            "model_name": "gemini-2.5-flash",
            "api_key": "AIza-demo",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        },
    )

    item = store.get_provider("gemini-main")
    assert item is not None
    assert item.provider_type == "gemini"
    assert item.model_name == "gemini-2.5-flash"
