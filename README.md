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
- 使用 JSON 儲存資料

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
invoice_ledger.json    本機資料檔
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

`invoice_ledger.json` 會保存目前輸入的發票、人員、金額、日期與備註資料。

若資料包含真實報帳內容、個資或敏感資訊，不建議提交到公開 GitHub repository。建議將正式資料保存在私有環境，或改接雲端資料庫。
