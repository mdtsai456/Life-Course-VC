# HTML lang 改成 zh-Hant 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `index.html` 的 `lang` 屬性從 `"en"` 改為 `"zh-Hant"`，讓 SEO 和無障礙工具正確辨識頁面語言。

**Architecture:** 單行修改，無其他檔案受影響。

**Tech Stack:** HTML

---

### Task 1: 修改 HTML lang 屬性

**Files:**
- Modify: `frontend/index.html:2`

- [ ] **Step 1: 修改 lang 屬性**

將第 2 行：
```html
<html lang="en">
```
改為：
```html
<html lang="zh-Hant">
```

- [ ] **Step 2: 驗證修改**

Run: `grep 'lang=' frontend/index.html`
Expected: `<html lang="zh-Hant">`

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "fix(i18n): change HTML lang from en to zh-Hant for SEO and accessibility"
```
