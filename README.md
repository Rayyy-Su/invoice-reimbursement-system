# Invoice Reimbursement System

發票對應人員對帳與撥款審核輔助系統。

線上系統：<https://invoice-reimbursement-system-testing.streamlit.app>

## 系統用途

本系統用於整理多張發票與多位成員之間的預先負擔金額，協助：

- 成員統計個別負擔金額與佔比
- 會計依發票核對每張發票總金額
- 主管檢視總花費與報表摘要
- 匯出 Excel 報表作為上繳、對帳與審核資料

## 主要功能

- 新增、刪除發票
- 新增、刪除人員
- 輸入每張發票中各成員負擔金額
- 編輯發票日期與內容備註
- 自動計算發票總金額
- 自動計算成員總負擔
- 自動計算整體總花費
- 顯示各發票總金額佔比圓餅圖
- 顯示各成員負擔費用佔比圓餅圖
- 匯出 Excel 報表
- 使用瀏覽器工作階段暫存資料，避免不同裝置共用紀錄

## 報表內容

Excel 匯出報表包含：

- 報表摘要
- 發票細節
- 對帳總表
- 發票佔比
- 成員佔比
- 原始明細

## 本機執行

安裝套件：

```bash
pip install -r requirements.txt
```

啟動 Streamlit：

```bash
streamlit run DT.py
```

或使用：

```bash
python3 -m streamlit run DT.py
```

## 專案檔案

```text
DT.py                  Streamlit 主程式
requirements.txt       Python 套件需求
```

## 部署到 Streamlit Community Cloud

部署時設定：

```text
Main file path: DT.py
```

必要檔案：

```text
DT.py
requirements.txt
```

## 資料安全提醒

部署版本使用 Streamlit session state 保存目前工作階段資料。

不同瀏覽器或不同裝置不會共用同一份紀錄；但重新整理、關閉頁面、雲端 App 休眠或重啟後，工作階段資料可能消失。請在送審前下載 Excel 報表留存。

若未來需要長期保存、多人協作或主管/會計審核流程，建議改接雲端資料庫。
