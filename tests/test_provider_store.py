from pathlib import Path

from researchclaw.providers.store import ProviderStore


def test_provider_store_save_list_remove(tmp_path: Path):
    store = ProviderStore(file_path=str(tmp_path / "providers.json"))

    store.save_provider(
        {
            "name": "openai-main",
            "provider_type": "openai",
            "model_name": "gpt-4o",
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
