# Custom Site-Specific Scrapers

This directory contains scrapers for individual event websites that don't fit into the main scraper framework.

## Usage

Add individual events using the `add_event.py` CLI tool:

```bash
# Test extraction (dry-run)
python add_event.py https://ivanjicatrail.rs/en/ --dry-run

# Add to races.jsonl
python add_event.py https://ivanjicatrail.rs/en/
```

## Creating New Scrapers

1. Copy the template:
   ```bash
   cp scrapers/custom/_template.py scrapers/custom/mysite_com.py
   ```

2. Edit the new file:
   - Update `SOURCE` constant
   - Change `@register_scraper("domain.com")` decorator
   - Customize selectors and extraction logic in the scrape function

3. Import the scraper in `add_event.py`:
   ```python
   import scrapers.custom.mysite_com  # noqa - registers scraper
   ```

4. Test it:
   ```bash
   python add_event.py https://mysite.com/event --dry-run
   ```

## Existing Scrapers

- `ivanjicatrail.py` - Ivanjica Trail (ivanjicatrail.rs)

## Tips

- Use `get_safe()` for regular HTML pages
- Use `get_selenium_safe()` for JavaScript-rendered pages
- Use CSS selectors (`.class`, `#id`, `tag.class`) for element selection
- Use `parse_date()`, `parse_distance_km()`, `clean_text()` helpers from `common.normalize`
- Always return `(Event, List[Race])` tuple
- Return `(None, [])` if scraping fails
