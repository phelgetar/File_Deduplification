# Makefile

VERSION ?= $(shell grep '^version:' version.yaml | awk '{print $$2}')
TAG_MSG ?= "🔖 Version $(VERSION) - Automated release"

.PHONY: release

release:
	@echo "🚀 Releasing version $(VERSION)..."
	@git add .
	@git commit -m "📦 Release version $(VERSION)"
	@git tag -a v$(VERSION) -m "$(TAG_MSG)"
	@git push origin main
	@git push origin v$(VERSION)
	@echo "✅ Release v$(VERSION) pushed to GitHub."
