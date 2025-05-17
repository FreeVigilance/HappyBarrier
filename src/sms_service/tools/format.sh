#!/bin/bash

echo "▶ Running black..."
black .

echo "▶ Running isort..."
isort .

echo "▶ Running ruff..."
ruff check .

echo "✅ All linters finished."
