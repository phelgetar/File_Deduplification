# Makefile

VERSION ?= $(shell grep '^version:' version.yaml | awk '{print $$2}')
TAG_MSG ?= "🔖 Version $(VERSION) - Automated release"
DATE := $(shell date +%Y-%m-%d)
TYPE ?= patch

.PHONY: release bump changelog

release:
	@echo "🚀 Releasing version $(VERSION)..."
	@git add .
	@git commit -m "📦 Release version $(VERSION)"
	@git tag -a v$(VERSION) -m "$(TAG_MSG)"
	@git push origin main
	@git push origin v$(VERSION)
	@make changelog

changelog:
	@echo "📘 Updating CHANGELOG.md..."
	@echo "\n## [v$(VERSION)] – $(DATE)" >> CHANGELOG.md
	@echo "\n- $(TAG_MSG)\n" >> CHANGELOG.md
	@git add CHANGELOG.md
	@git commit -m "📝 Update CHANGELOG for v$(VERSION)" || echo "No changelog changes"
	@git push origin main

bump:
	@echo "🔧 Bumping $(TYPE) version..."
	@python scripts/bump_version.py $(TYPE)
	@git add version.yaml
	@git commit -m "🔼 Bump $(TYPE) version"
	@git push origin main
