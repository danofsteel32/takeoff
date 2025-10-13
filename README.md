# Takeoff

Create material takeoffs from PDF blueprints. The plan is to use an LLM to perform
structured data extraction against a blueprints text and visual renderings.

There are also plans to create synthetic data using [ezdxf](https://ezdxf.readthedocs.io/).

## Usage

Currently we don't do much but you can see the beginnings of the system used to chunk
the PDF into textual and visual chunks.

```bash
uv run takeoff blueprint.pdf -vv
```
