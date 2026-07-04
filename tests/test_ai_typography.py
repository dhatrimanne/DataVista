from frontend.components.ai_typography import preserve_currency_markdown


def test_preserve_currency_markdown_escapes_currency_without_touching_existing_escapes():
    text = "California ($457,687.63) and New York ($310,876.27). Already escaped: \\$2.30M."

    rendered = preserve_currency_markdown(text)

    assert rendered == "California (\\$457,687.63) and New York (\\$310,876.27). Already escaped: \\$2.30M."
