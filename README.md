# MyBible-CLI Extensions Repository

This repository contains community-contributed extensions for [MyBible-CLI](https://github.com/kosivantsov/mybible-cli-java), including themes, book name mappings, localizations, and extension bundles.

## Extension Types

### 1. Theme Extensions

Customize the appearance of MyBible-CLI with custom color schemes, fonts, and styling.

**Example: `manifest.json`**
```
{
  "name": "dracula-dark",
  "version": "1.0.0",
  "type": "theme",
  "description": "Dracula dark theme for MyBible-CLI",
  "author": "Dracula Team",
  "files": {
    "themes": ["dracula.json"]
  }
}
```

### 2. Mapping Extensions

Add custom book name abbreviations and alternative names for different languages.

**Language Support:** Mapping extensions may specify which languages they support via `languages` (array of language names in that language) and `lang_codes` (array of BCP47 language codes).

**Example: `manifest.json`**
```
{
  "name": "german-book-names",
  "version": "1.0.0",
  "type": "mapping",
  "description": "German Bible book names and abbreviations",
  "author": "Hans Mueller",
  "languages": ["Deutsch"],
  "lang_codes": ["de"],
  "files": {
    "mappings": ["de_mapping.json"]
  }
}
```

### 3. Localization Extensions

Translate MyBible-CLI interface into different languages.

**Language Support:** Localization extensions must specify the supported languages and their BCP47 codes with `languages` and `lang_codes` fields. This allows users to filter extensions in the GUI/CLI by language code.

**Example: `manifest.json`**
```
{
  "name": "spanish-localization",
  "version": "1.0.0",
  "type": "localization",
  "description": "Spanish translation for MyBible-CLI",
  "author": "Maria Garcia",
  "languages": ["Español"],
  "lang_codes": ["es"],
  "files": {
    "resources": ["messages_es.properties", "gui_es.properties"]
  }
}
```

### 4. Bundle Extensions

Combine multiple extension types for a complete language/regional package.

**Language Support:** Bundles can specify multiple languages/codes they cover, e.g. `["Français", "English"]` for languages and `["fr", "en"]` for lang_codes.

**Example: `manifest.json`**
```
{
  "name": "french-complete",
  "version": "2.0.0",
  "type": "bundle",
  "description": "Complete French package with translations, mappings, and theme",
  "author": "Pierre Dubois",
  "languages": ["Français"],
  "lang_codes": ["fr"],
  "files": {
    "mappings": ["fr_mapping.json"],
    "resources": ["messages_fr.properties", "gui_fr.properties"],
    "themes": ["french_classic.json"]
  }
}
```

## Language Attributes in Extensions

If the extension is of type `mapping`, `localization`, or `bundle`, include:
- **`languages`**: List of language names in their native script (e.g., `["Español", "Русский"]`)
- **`lang_codes`**: List of [BCP47 language codes](https://en.wikipedia.org/wiki/IETF_language_tag) (e.g., `["es", "ru"]`)

These attributes help users filter and identify extensions by their language of support in both CLI and GUI. Both arrays must be present and have the same length.

## Installing Extensions

### From GUI
1. Open MyBible-CLI
2. Go to Configuration → Extensions
3. Browse available extensions (can filter by language code)
4. Click "Install" on desired extension

### From CLI
```
mybible ext --update
mybible ext --list available --language es
mybible ext --install spanish-localization
```

## Publishing Extensions

### Prerequisites
- Python 3.6 or higher
- Git

### Steps

1. **Create your extension files** and package them with a `manifest.json`

2. **Create a zip file**:
```
zip my-extension.zip manifest.json your-files.json
```

3. **Clone this repository**:
```
git clone https://github.com/kosivantsov/mybible-cli-extensions.git
cd mybible-cli-extensions
```

4. **Publish your extension**:
```
./scripts/publish.py /path/to/my-extension.zip
```

5. **Commit and push**:

After publishing, the script will create platform-specific commit scripts:
- On **Linux/Mac**: Run `./scripts/commit-and-push.sh`
- On **Windows**: Run `scripts\commit-and-push.cmd`

These scripts will automatically commit and push your changes.

For contributors: Fork this repository and submit a pull request.

## Extension Structure

Each extension must include a `manifest.json` file with the following required fields:

- `name` - Unique extension identifier (lowercase, hyphens only)
- `version` - Semantic version (X.Y.Z)
- `type` - Extension type (`theme`, `mapping`, `localization`, or `bundle`)
- `description` - Brief description of the extension
- `author` - Extension author name
- `files` - Object containing arrays of files by category
- (Optional, but **recommended** for mappings/localizations/bundles):
  - `languages` — Array of language names (in native script)
  - `lang_codes` — Array of BCP47 language codes

## File Format Specifications

### Theme Files (`*.json`)
Must include: `lookAndFeelClassName`, `formatString`, `styles`, `textAreaBackground`

### Mapping Files (`*_mapping.json`)
- Must follow naming pattern: `*_mapping.json` (e.g., `de_mapping.json`)
- Top-level keys must be numeric book numbers (10, 20, 30, etc.)

### Resource Files (`*.properties`)
- Must follow naming pattern: `(messages|gui)_<lang>.properties` or `(messages|gui)_<lang>_<COUNTRY>.properties`
- Standard Java properties format with key=value pairs

## Support

For issues or questions:
- [MyBible-CLI Issues](https://github.com/kosivantsov/mybible-cli-java/issues)
- [Extension Repository Issues](https://github.com/kosivantsov/mybible-cli-extensions/issues)

## License

Extensions in this repository are contributed by their respective authors. Please check individual extension licenses.