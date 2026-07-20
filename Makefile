# Makefile

VERSION ?= $(shell grep '^version:' scripts/version.yaml | awk '{print $$2}')
TAG_MSG ?= "🔖 Version $(VERSION) - Automated release"
DATE := $(shell date +%Y-%m-%d)
TYPE ?= patch

.PHONY: release bump changelog

release:
	@echo "🚀 Releasing version $(shell python scripts/read_version.py)..."
	@echo "🔎 Checking staged files for size violations (>100MB)..."
	@if git diff --cached --name-only | xargs -I{} find {} -type f -size +100M | grep -q .; then \
		echo "❌ One or more files exceed GitHub’s 100MB limit."; exit 1; \
	else \
		echo "✅ All staged files are under the 100MB limit."; \
	fi
	git commit -am "📦 Release version $(shell python scripts/read_version.py)" || true
	git push origin main
	@echo "📘 Creating GitHub release..."
	gh release create v$(shell python scripts/read_version.py) --title "v$(shell python scripts/read_version.py)" --notes-file docs/CHANGELOG_LAST.md

# release:
# 	@echo "🚀 Releasing version $(VERSION)..."
# 	@git add .
# 	@git commit -m "📦 Release version $(VERSION)"
# 	@git tag -a v$(VERSION) -m "$(TAG_MSG)"
# 	@git push origin main
# 	@git push origin v$(VERSION)
# 	@make changelog

changelog:
	@echo "📘 Updating CHANGELOG.md..."
	python3 scripts/gen_changelog.py > docs/CHANGELOG_LAST.md
	python3 scripts/gen_changelog.py >> CHANGELOG.md
	git add CHANGELOG.md
	$(MAKE) check_size
	git commit -m "📝 Update CHANGELOG for v$(VERSION)" || true
	git push origin main

# changelog:
# 	@echo "📘 Updating CHANGELOG.md..."
# 	@echo "\n## [v$(VERSION)] – $(DATE)" >> CHANGELOG.md
# 	@echo "\n- $(TAG_MSG)\n" >> CHANGELOG.md
# 	@git add CHANGELOG.md
# 	@git commit -m "📝 Update CHANGELOG for v$(VERSION)" || echo "No changelog changes"
# 	@git push origin main

bump:
	@echo "🔧 Bumping $(TYPE) version..."
	@python scripts/bump_version.py $(TYPE)
	@git add scripts/version.yaml
	@git commit -m "🔼 Bump $(TYPE) version"
	@git push origin main
