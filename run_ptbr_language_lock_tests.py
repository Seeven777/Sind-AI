from cognitive.language_guard import looks_english_dominant, ensure_portuguese_response


class FakeModels:
    def __init__(self, output):
        self.output = output
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        return {"message": {"content": self.output}, "_jarvis_model": "fake"}


def test_portuguese_passes_without_second_call():
    model = FakeModels("não deveria ser usado")
    text = "Consigo ajudar com essa tarefa. O observador está ativo e o histórico foi preservado."
    out = ensure_portuguese_response(text, model, user_text="teste")
    assert out == text
    assert model.calls == 0


def test_screenshot_english_is_detected():
    text = (
        "I encountered an internal error while trying to process your request. "
        "Let's try again from the beginning. How can I assist you today?"
    )
    assert looks_english_dominant(text)


def test_english_is_rewritten():
    model = FakeModels(
        "Encontrei um erro interno ao processar sua solicitação. "
        "Vamos tentar novamente desde o início. Como posso ajudar?"
    )
    text = "I encountered an internal error while trying to process your request. How can I assist you today?"
    out = ensure_portuguese_response(text, model, user_text="olá")
    assert "erro interno" in out.lower()
    assert not looks_english_dominant(out)
    assert model.calls == 1


def test_code_is_preserved_from_false_positive():
    model = FakeModels("não deveria ser usado")
    text = """Use este comando:
```bash
git status
git add .
git commit -m "test"
```
Depois verifique se o commit foi criado corretamente."""
    out = ensure_portuguese_response(text, model, user_text="teste")
    assert out == text
    assert model.calls == 0


def test_failed_rewrite_never_exposes_english():
    model = FakeModels("I am sorry, please try again.")
    text = "I encountered an internal error. Please try again."
    out = ensure_portuguese_response(text, model, user_text="teste")
    assert out.startswith("Ocorreu uma falha")
    assert not looks_english_dominant(out)


if __name__ == "__main__":
    tests = [
        test_portuguese_passes_without_second_call,
        test_screenshot_english_is_detected,
        test_english_is_rewritten,
        test_code_is_preserved_from_false_positive,
        test_failed_rewrite_never_exposes_english,
    ]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"[OK] {t.__name__}")
    print(f"\n{passed}/{len(tests)} testes passaram.")
