# WL-Blogger

WL-Blogger is a Python-based content generation and WordPress publishing system that automates the creation and management of technical blog articles.

## Features

- Automated topic generation with AI-powered content creation
- WordPress integration for direct publishing
- Image generation capabilities using DALL-E or Flux Pro
- Article validation and schema checking
- Configurable content templates and prompts
- Markdown to WordPress HTML conversion
- Media management and compression

## Project Structure

```
wl-blogger/
├── assets/
│   └── articles/         # Generated articles and assets
├── kackle/              # Core application code
├── prompt_validator/    # Schema validation tools
├── prompts/            # Content generation prompts
└── wordpress_logs/     # WordPress operation logs
```

## Core Components

- `ArticleGenerator`: Creates and manages blog articles
- `TopicGenerator`: Generates unique blog topics
- `WordPressAPIClient`: Handles WordPress integration
- `SchemaValidator`: Validates content structure
- `PromptManager`: Manages AI content generation

## Requirements

- Python 3.8+
- OpenAI API access
- WordPress site with REST API access
- Replicate API access (for Flux Pro image generation)

## Configuration

Create a `config.yaml` file with:

```yaml
folders:
  articles: path/to/articles
  images: path/to/images
  prompts: path/to/prompts

openai:
  api_key: your_key
  organization_id: your_org_id
  llm-model: model_name

wordpress:
  url: your_wp_site_url
  username: your_username
  password: your_password

replicate:
  api_key: your_key
  image-model: model_name
  width: 512
  height: 512
```

## Usage

Generate topics:
```bash
python -m kackle --topic --from-date 2024-01-01 --count 5
```

Generate articles:
```bash
python -m kackle --article --from-date 2024-01-01 --count 5
```

Upload article:
```bash
python -m kackle --upload --file path/to/article.yaml
```

## Error Handling

- Logs are stored in `wordpress_logs/`
- Failed operations create detailed error reports
- Validation errors include specific schema violations

## Development

- Use `SchemaValidator` for content validation
- Follow existing patterns for API integrations
- Handle media assets with proper compression
- Implement proper error logging and recovery

## License

BSD 3