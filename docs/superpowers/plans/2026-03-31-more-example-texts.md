# 多加範例文字 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在現有「日常」和「正式」兩個範例文字之外，新增「故事」和「新聞」範例，讓使用者更容易試用語音克隆功能。

**Architecture:** 在 `EXAMPLE_TEXTS` 陣列中新增兩個物件，並確保 CSS 支援換行以容納更多按鈕。

**Tech Stack:** React (JSX), CSS

---

### Task 1: 新增範例文字並修正 CSS 換行

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx:51-54`
- Modify: `frontend/src/index.css:214-220`

- [ ] **Step 1: 新增「故事」和「新聞」範例文字**

在 `frontend/src/components/VoiceCloner.jsx` 第 51-54 行，將 `EXAMPLE_TEXTS` 改為：

```javascript
const EXAMPLE_TEXTS = [
  { label: '日常', text: '嗨，你好嗎？今天天氣真不錯，一起出去走走吧！' },
  { label: '正式', text: '各位觀眾大家好，歡迎收聽今天的節目，我是你們的主持人。' },
  { label: '故事', text: '從前從前，在一座大山的腳下，住著一位善良的老爺爺。' },
  { label: '新聞', text: '根據最新報導，本週氣溫將持續回暖，預計週末會迎來晴朗好天氣。' },
]
```

- [ ] **Step 2: 為 CSS 加上 `flex-wrap: wrap` 以防按鈕過多時換行**

在 `frontend/src/index.css` 第 214-220 行，將 `.example-texts` 改為：

```css
.example-texts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: #666;
}
```

- [ ] **Step 3: 手動驗證**

Run: 在瀏覽器中開啟應用，確認四個範例按鈕（日常、正式、故事、新聞）都正常顯示，點擊後文字正確填入輸入框。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/VoiceCloner.jsx frontend/src/index.css
git commit -m "feat: add story and news example texts for voice cloning"
```
