from __future__ import annotations

import json
from datetime import date, datetime
from io import BytesIO
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


Money = Decimal
DATA_FILE = Path("invoice_ledger.json")
INVOICE_TOTAL_COLUMN = "發票總金額"
MEMBER_TOTAL_LABEL = "成員總負擔"


def parse_money(value: object) -> Money:
    if pd.isna(value):
        return Decimal("0")

    try:
        amount = Decimal(str(value).strip() or "0")
    except InvalidOperation as error:
        raise ValueError("金額格式錯誤，請輸入數字，例如 1200 或 99.5") from error

    if amount < 0:
        raise ValueError("金額不可為負數")

    return amount


def format_money(value: Money) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return f"{value.normalize():f}"


@dataclass
class InvoiceLedger:
    invoices: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    amounts: dict[str, dict[str, Money]] = field(default_factory=dict)
    invoice_details: dict[str, dict[str, str]] = field(default_factory=dict)

    def add_invoice(self, invoice_id: str, invoice_date: str = "", note: str = "") -> None:
        invoice_id = invoice_id.strip()
        if not invoice_id:
            raise ValueError("發票名稱不可為空")
        if invoice_id in self.invoices:
            raise ValueError(f"發票已存在：{invoice_id}")

        self.invoices.append(invoice_id)
        self.amounts[invoice_id] = {member: Decimal("0") for member in self.members}
        self.invoice_details[invoice_id] = {
            "date": invoice_date.strip(),
            "note": note.strip(),
        }

    def add_member(self, member_name: str) -> None:
        member_name = member_name.strip()
        if not member_name:
            raise ValueError("人員名稱不可為空")
        if member_name in self.members:
            raise ValueError(f"人員已存在：{member_name}")

        self.members.append(member_name)
        for invoice_id in self.invoices:
            self.amounts[invoice_id][member_name] = Decimal("0")

    def delete_invoice(self, invoice_id: str) -> None:
        self._ensure_invoice(invoice_id)
        self.invoices.remove(invoice_id)
        self.amounts.pop(invoice_id, None)
        self.invoice_details.pop(invoice_id, None)

    def delete_member(self, member_name: str) -> None:
        self._ensure_member(member_name)
        self.members.remove(member_name)
        for invoice_amounts in self.amounts.values():
            invoice_amounts.pop(member_name, None)

    def clear(self) -> None:
        self.invoices.clear()
        self.members.clear()
        self.amounts.clear()
        self.invoice_details.clear()

    def set_amount(self, invoice_id: str, member_name: str, amount: Money) -> None:
        self._ensure_invoice(invoice_id)
        self._ensure_member(member_name)
        self.amounts[invoice_id][member_name] = amount

    def set_invoice_details(self, invoice_id: str, invoice_date: str, note: str) -> None:
        self._ensure_invoice(invoice_id)
        self.invoice_details[invoice_id] = {
            "date": str(invoice_date).strip(),
            "note": str(note).strip(),
        }

    def row_sum(self, invoice_id: str) -> Money:
        self._ensure_invoice(invoice_id)
        return sum(self.amounts[invoice_id].values(), Decimal("0"))

    def column_sum(self, member_name: str) -> Money:
        self._ensure_member(member_name)
        return sum(
            self.amounts[invoice_id][member_name]
            for invoice_id in self.invoices
        )

    def total(self) -> Money:
        return sum((self.row_sum(invoice_id) for invoice_id in self.invoices), Decimal("0"))

    def member_ratio(self, member_name: str) -> Decimal:
        total = self.total()
        if total == 0:
            return Decimal("0")
        return self.column_sum(member_name) / total * Decimal("100")

    def invoice_ratio(self, invoice_id: str) -> Decimal:
        total = self.total()
        if total == 0:
            return Decimal("0")
        return self.row_sum(invoice_id) / total * Decimal("100")

    def to_entry_dataframe(self) -> pd.DataFrame:
        rows = []
        for invoice_id in self.invoices:
            row = {"發票": invoice_id}
            for member in self.members:
                row[member] = float(self.amounts[invoice_id].get(member, Decimal("0")))
            rows.append(row)

        return pd.DataFrame(rows, columns=["發票", *self.members])

    def invoice_details_dataframe(self) -> pd.DataFrame:
        rows = []
        for invoice_id in self.invoices:
            detail = self.invoice_details.get(invoice_id, {})
            rows.append(
                {
                    "發票": invoice_id,
                    "發票日期": detail.get("date", ""),
                    "內容備註": detail.get("note", ""),
                }
            )
        return pd.DataFrame(rows, columns=["發票", "發票日期", "內容備註"])

    def to_summary_dataframe(self) -> pd.DataFrame:
        if not self.invoices and not self.members:
            return pd.DataFrame()

        rows = []
        for invoice_id in self.invoices:
            row = {"發票": invoice_id}
            for member in self.members:
                row[member] = float(self.amounts[invoice_id].get(member, Decimal("0")))
            row[INVOICE_TOTAL_COLUMN] = float(self.row_sum(invoice_id))
            rows.append(row)

        footer = {"發票": MEMBER_TOTAL_LABEL}
        for member in self.members:
            footer[member] = float(self.column_sum(member))
        footer[INVOICE_TOTAL_COLUMN] = float(self.total())
        rows.append(footer)

        return pd.DataFrame(rows, columns=["發票", *self.members, INVOICE_TOTAL_COLUMN])

    def ratio_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "成員": self.members,
                "負擔金額": [float(self.column_sum(member)) for member in self.members],
                "比例": [float(self.member_ratio(member)) for member in self.members],
            }
        )

    def invoice_ratio_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "發票": self.invoices,
                "總金額": [float(self.row_sum(invoice_id)) for invoice_id in self.invoices],
                "比例": [float(self.invoice_ratio(invoice_id)) for invoice_id in self.invoices],
            }
        )

    def detail_dataframe(self) -> pd.DataFrame:
        rows = []
        for invoice_id in self.invoices:
            detail = self.invoice_details.get(invoice_id, {})
            for member in self.members:
                rows.append(
                    {
                        "發票": invoice_id,
                        "發票日期": detail.get("date", ""),
                        "內容備註": detail.get("note", ""),
                        "成員": member,
                        "負擔金額": float(self.amounts[invoice_id].get(member, Decimal("0"))),
                    }
                )
        return pd.DataFrame(rows, columns=["發票", "發票日期", "內容備註", "成員", "負擔金額"])

    def to_json(self) -> dict:
        return {
            "invoices": self.invoices,
            "members": self.members,
            "amounts": {
                invoice_id: {
                    member: format_money(amount)
                    for member, amount in member_amounts.items()
                }
                for invoice_id, member_amounts in self.amounts.items()
            },
            "invoice_details": self.invoice_details,
        }

    @classmethod
    def from_json(cls, payload: dict) -> InvoiceLedger:
        ledger = cls(
            invoices=list(payload.get("invoices", [])),
            members=list(payload.get("members", [])),
        )
        raw_amounts = payload.get("amounts", {})
        raw_details = payload.get("invoice_details", {})
        ledger.amounts = {
            invoice_id: {
                member: parse_money(raw_amounts.get(invoice_id, {}).get(member, "0"))
                for member in ledger.members
            }
            for invoice_id in ledger.invoices
        }
        ledger.invoice_details = {
            invoice_id: {
                "date": str(raw_details.get(invoice_id, {}).get("date", "")),
                "note": str(raw_details.get(invoice_id, {}).get("note", "")),
            }
            for invoice_id in ledger.invoices
        }
        return ledger

    def save(self, path: Path = DATA_FILE) -> None:
        path.write_text(
            json.dumps(self.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path = DATA_FILE) -> InvoiceLedger:
        if not path.exists():
            return cls()

        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_json(payload)

    def _ensure_invoice(self, invoice_id: str) -> None:
        if invoice_id not in self.invoices:
            raise ValueError(f"找不到發票：{invoice_id}")

    def _ensure_member(self, member_name: str) -> None:
        if member_name not in self.members:
            raise ValueError(f"找不到人員：{member_name}")


def load_ledger() -> InvoiceLedger:
    if "ledger" not in st.session_state:
        st.session_state.ledger = InvoiceLedger.load()
    return st.session_state.ledger


def save_ledger() -> None:
    st.session_state.ledger.save()


def handle_error(action) -> bool:
    try:
        action()
        return True
    except ValueError as error:
        st.sidebar.error(str(error))
        return False


def render_sidebar(ledger: InvoiceLedger) -> None:
    st.sidebar.header("資料管理")
    st.sidebar.caption(f"儲存檔案：`{DATA_FILE}`")

    with st.sidebar.form("add_invoice_form", clear_on_submit=True):
        invoice_id = st.text_input("新增發票", placeholder="例如 INV-001")
        invoice_date = st.date_input("發票日期", value=date.today())
        invoice_note = st.text_area("內容備註", placeholder="例如 住宿費、交通費、採購項目")
        submitted = st.form_submit_button("新增發票")
        if submitted:
            if handle_error(lambda: ledger.add_invoice(invoice_id, invoice_date.isoformat(), invoice_note)):
                save_ledger()
                st.rerun()

    with st.sidebar.form("add_member_form", clear_on_submit=True):
        member_name = st.text_input("新增人員", placeholder="例如 Wang")
        submitted = st.form_submit_button("新增人員")
        if submitted:
            if handle_error(lambda: ledger.add_member(member_name)):
                save_ledger()
                st.rerun()

    with st.sidebar.expander("刪除與清除"):
        if ledger.invoices:
            invoice_to_delete = st.selectbox("刪除發票", ledger.invoices)
            if st.button("刪除選取發票", width="stretch"):
                if handle_error(lambda: ledger.delete_invoice(invoice_to_delete)):
                    save_ledger()
                    st.rerun()
        else:
            st.caption("目前沒有可刪除的發票。")

        if ledger.members:
            member_to_delete = st.selectbox("刪除人員", ledger.members)
            if st.button("刪除選取人員", width="stretch"):
                if handle_error(lambda: ledger.delete_member(member_to_delete)):
                    save_ledger()
                    st.rerun()
        else:
            st.caption("目前沒有可刪除的人員。")

        confirm_clear = st.checkbox("確認清除全部資料")
        if st.button("全部清除", width="stretch", disabled=not confirm_clear):
            ledger.clear()
            save_ledger()
            st.rerun()

    if st.sidebar.button("儲存目前資料", width="stretch"):
        save_ledger()
        st.sidebar.success("已儲存")

    render_export_controls(ledger)

    with st.sidebar.expander("JSON 原始資料"):
        st.json(ledger.to_json())


def render_export_controls(ledger: InvoiceLedger) -> None:
    st.sidebar.header("匯出報表")
    report_time = datetime.now()
    excel_bytes = build_excel_report(ledger, report_time)
    filename = f"invoice_reconciliation_{report_time:%Y%m%d_%H%M%S}.xlsx"

    st.sidebar.download_button(
        "下載 Excel 報表",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        disabled=not ledger.invoices and not ledger.members,
    )


def build_excel_report(ledger: InvoiceLedger, report_time: datetime) -> bytes:
    output = BytesIO()
    summary_df = ledger.to_summary_dataframe()
    invoice_ratio_df = ledger.invoice_ratio_dataframe()
    member_ratio_df = ledger.ratio_dataframe()
    detail_df = ledger.detail_dataframe()
    invoice_details_df = ledger.invoice_details_dataframe()
    overview_df = pd.DataFrame(
        [
            {"項目": "報表名稱", "內容": "發票對應人員對帳報表"},
            {"項目": "產生時間", "內容": report_time.strftime("%Y-%m-%d %H:%M:%S")},
            {"項目": "發票數量", "內容": len(ledger.invoices)},
            {"項目": "成員數量", "內容": len(ledger.members)},
            {"項目": "總金額", "內容": f"{format_money(ledger.total())} TWD"},
        ]
    )

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        overview_df.to_excel(writer, sheet_name="報表摘要", index=False)
        invoice_details_df.to_excel(writer, sheet_name="發票細節", index=False)
        summary_df.to_excel(writer, sheet_name="對帳總表", index=False)
        invoice_ratio_df.to_excel(writer, sheet_name="發票佔比", index=False)
        member_ratio_df.to_excel(writer, sheet_name="成員佔比", index=False)
        detail_df.to_excel(writer, sheet_name="原始明細", index=False)

        workbook = writer.book
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#1f2937", "font_color": "#ffffff", "border": 1}
        )
        invoice_total_format = workbook.add_format(
            {"bold": True, "bg_color": "#111111", "font_color": "#ffffff", "border": 1, "num_format": "#,##0.00"}
        )
        member_total_format = workbook.add_format(
            {"bold": True, "bg_color": "#111111", "font_color": "#ffffff", "border": 1, "num_format": "#,##0.00"}
        )
        grand_total_format = workbook.add_format(
            {"bold": True, "bg_color": "#17324d", "font_color": "#ffffff", "border": 1}
        )
        money_format = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_format = workbook.add_format({"border": 1})
        total_card_format = workbook.add_format(
            {"bold": True, "font_size": 16, "bg_color": "#eaf3ff", "font_color": "#17324d", "border": 1}
        )

        format_excel_sheet(writer.sheets["報表摘要"], overview_df, header_format, text_format)
        writer.sheets["報表摘要"].set_column(0, 0, 16)
        writer.sheets["報表摘要"].set_column(1, 1, 32)
        writer.sheets["報表摘要"].write(6, 0, "總金額", header_format)
        writer.sheets["報表摘要"].write(6, 1, f"{format_money(ledger.total())} TWD", total_card_format)

        format_excel_sheet(writer.sheets["發票細節"], invoice_details_df, header_format, text_format)
        format_excel_sheet(writer.sheets["對帳總表"], summary_df, header_format, text_format, money_format)
        apply_summary_excel_highlights(
            writer.sheets["對帳總表"],
            summary_df,
            invoice_total_format,
            member_total_format,
            grand_total_format,
        )

        format_excel_sheet(writer.sheets["發票佔比"], invoice_ratio_df, header_format, text_format, money_format)
        format_excel_sheet(writer.sheets["成員佔比"], member_ratio_df, header_format, text_format, money_format)
        format_excel_sheet(writer.sheets["原始明細"], detail_df, header_format, text_format, money_format)

    output.seek(0)
    return output.getvalue()


def format_excel_sheet(
    worksheet,
    dataframe: pd.DataFrame,
    header_format,
    text_format,
    money_format=None,
) -> None:
    for column_index, column_name in enumerate(dataframe.columns):
        worksheet.write(0, column_index, column_name, header_format)
        column_values = [str(value) for value in dataframe[column_name].tolist()]
        best_width = max([len(str(column_name)), *[len(value) for value in column_values]], default=10)
        worksheet.set_column(column_index, column_index, min(max(best_width + 2, 12), 28))

        body_format = money_format if pd.api.types.is_numeric_dtype(dataframe[column_name]) and money_format else text_format
        for row_index, value in enumerate(dataframe[column_name], start=1):
            worksheet.write(row_index, column_index, value, body_format)

    worksheet.freeze_panes(1, 0)


def apply_summary_excel_highlights(
    worksheet,
    summary_df: pd.DataFrame,
    invoice_total_format,
    member_total_format,
    grand_total_format,
) -> None:
    if summary_df.empty:
        return

    invoice_total_col = summary_df.columns.get_loc(INVOICE_TOTAL_COLUMN)
    for row_index, row in summary_df.iterrows():
        excel_row = row_index + 1
        if row["發票"] == MEMBER_TOTAL_LABEL:
            for column_index, value in enumerate(row):
                worksheet.write(excel_row, column_index, value, member_total_format)
            worksheet.write(
                excel_row,
                invoice_total_col,
                f"總花費: {format_money(parse_money(row[INVOICE_TOTAL_COLUMN]))} TWD",
                grand_total_format,
            )
        else:
            worksheet.write(excel_row, invoice_total_col, row[INVOICE_TOTAL_COLUMN], invoice_total_format)


def update_ledger_from_editor(ledger: InvoiceLedger, edited_df: pd.DataFrame) -> None:
    for _, row in edited_df.iterrows():
        invoice_id = str(row["發票"])
        for member in ledger.members:
            ledger.set_amount(invoice_id, member, parse_money(row.get(member, 0)))


def update_invoice_details_from_editor(ledger: InvoiceLedger, edited_df: pd.DataFrame) -> None:
    for _, row in edited_df.iterrows():
        invoice_id = str(row["發票"])
        ledger.set_invoice_details(
            invoice_id,
            str(row.get("發票日期", "") or ""),
            str(row.get("內容備註", "") or ""),
        )


def render_invoice_details_editor(ledger: InvoiceLedger) -> None:
    if not ledger.invoices:
        return

    st.subheader("發票細節")
    edited_df = st.data_editor(
        ledger.invoice_details_dataframe(),
        key="invoice_details_editor",
        hide_index=True,
        width="stretch",
        disabled=["發票"],
        column_config={
            "發票": st.column_config.TextColumn("發票", disabled=True),
            "發票日期": st.column_config.TextColumn("發票日期", help="建議格式：YYYY-MM-DD"),
            "內容備註": st.column_config.TextColumn("內容備註"),
        },
    )
    update_invoice_details_from_editor(ledger, edited_df)
    save_ledger()


def render_editor(ledger: InvoiceLedger) -> None:
    if not ledger.invoices or not ledger.members:
        st.info("請先在左側新增至少一張發票與一位人員。")
        return

    st.subheader("金額輸入")
    entry_df = ledger.to_entry_dataframe()
    edited_df = st.data_editor(
        entry_df,
        key="amount_editor",
        hide_index=True,
        width="stretch",
        disabled=["發票"],
        column_config={
            "發票": st.column_config.TextColumn("發票", disabled=True),
            **{
                member: st.column_config.NumberColumn(
                    member,
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                )
                for member in ledger.members
            },
        },
    )

    update_ledger_from_editor(ledger, edited_df)
    save_ledger()


def render_summary(ledger: InvoiceLedger) -> None:
    st.subheader("對帳表")
    summary_df = ledger.to_summary_dataframe()
    if summary_df.empty:
        st.dataframe(pd.DataFrame(columns=["發票", INVOICE_TOTAL_COLUMN]), hide_index=True, width="stretch")
        return

    display_df = summary_display_dataframe(summary_df)
    styled_summary = style_summary_dataframe(display_df)
    st.dataframe(
        styled_summary,
        hide_index=True,
        width="stretch",
    )


def render_total(ledger: InvoiceLedger) -> None:
    st.subheader("總金額")
    st.markdown(
        f"""
        <div style="
            background: #eaf3ff;
            border: 1px solid #9ec5fe;
            border-radius: 8px;
            padding: 18px 20px;
        ">
            <div style="font-size: 2.1rem; color: #17324d; font-weight: 800; line-height: 1.25;">
                {format_money(ledger.total())} TWD
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summary_display_dataframe(summary_df: pd.DataFrame) -> pd.DataFrame:
    display_df = summary_df.copy()
    numeric_columns = [column for column in display_df.columns if column != "發票"]
    for column in numeric_columns:
        display_df[column] = display_df[column].map(lambda value: f"{value:,.2f}")

    if not display_df.empty:
        last_row_index = display_df.index[-1]
        display_df.loc[last_row_index, INVOICE_TOTAL_COLUMN] = (
            f"總花費: {format_money(parse_money(summary_df.loc[last_row_index, INVOICE_TOTAL_COLUMN]))} TWD"
        )

    return display_df


def style_summary_dataframe(summary_df: pd.DataFrame) -> pd.io.formats.style.Styler:
    def highlight_cells(row: pd.Series) -> list[str]:
        styles = []
        is_member_total_row = row["發票"] == MEMBER_TOTAL_LABEL
        for column in summary_df.columns:
            is_grand_total_cell = is_member_total_row and column == INVOICE_TOTAL_COLUMN
            if is_grand_total_cell:
                styles.append("background-color: #17324d; color: #ffffff; font-weight: 800;")
            elif is_member_total_row:
                styles.append("background-color: #111111; color: #ffffff; font-weight: 700;")
            elif column == INVOICE_TOTAL_COLUMN:
                styles.append("background-color: #111111; color: #ffffff; font-weight: 700;")
            else:
                styles.append("")
        return styles

    invoice_total_col = summary_df.columns.get_loc(INVOICE_TOTAL_COLUMN)
    return (
        summary_df.style
        .apply(highlight_cells, axis=1)
        .set_table_styles(
            [
                {
                    "selector": f"th.col_heading.level0.col{invoice_total_col}",
                    "props": [("font-weight", "800")],
                }
            ],
            overwrite=False,
        )
    )


def pie_chart(data: pd.DataFrame, name_column: str, value_column: str) -> alt.Chart:
    return (
        alt.Chart(data)
        .mark_arc(innerRadius=55, outerRadius=135)
        .encode(
            theta=alt.Theta(f"{value_column}:Q", stack=True),
            color=alt.Color(
                f"{name_column}:N",
                legend=alt.Legend(title=None, orient="bottom"),
                scale=alt.Scale(scheme="tableau20"),
            ),
            tooltip=[
                alt.Tooltip(f"{name_column}:N", title=name_column),
                alt.Tooltip(f"{value_column}:Q", title=value_column, format=",.2f"),
                alt.Tooltip("比例:Q", title="比例", format=".2f"),
            ],
        )
        .properties(height=430)
        .configure_view(stroke=None)
    )


def render_ratio_table(
    data: pd.DataFrame,
    amount_column: str,
    empty_message: str,
) -> None:
    if data.empty:
        st.caption(empty_message)
        return

    st.dataframe(
        data,
        hide_index=True,
        width="stretch",
        column_config={
            amount_column: st.column_config.NumberColumn(amount_column, format="%.2f"),
            "比例": st.column_config.NumberColumn("比例", format="%.2f%%"),
        },
    )


def render_pie_charts(ledger: InvoiceLedger) -> None:
    st.subheader("佔比圓餅圖")

    invoice_ratio_df = ledger.invoice_ratio_dataframe()
    member_ratio_df = ledger.ratio_dataframe()

    invoice_col, member_col = st.columns(2)
    with invoice_col:
        st.markdown("**各發票對應總金額佔比**")
        if ledger.total() > 0 and not invoice_ratio_df.empty:
            st.altair_chart(
                pie_chart(invoice_ratio_df, "發票", "總金額"),
                width="stretch",
            )
        render_ratio_table(invoice_ratio_df, "總金額", "目前尚無發票資料。")

    with member_col:
        st.markdown("**各成員負擔費用佔比**")
        if ledger.total() > 0 and not member_ratio_df.empty:
            st.altair_chart(
                pie_chart(member_ratio_df, "成員", "負擔金額"),
                width="stretch",
            )
        render_ratio_table(member_ratio_df, "負擔金額", "目前尚無人員資料。")


def main() -> None:
    st.set_page_config(
        page_title="發票對應人員對帳系統",
        layout="wide",
    )

    ledger = load_ledger()
    render_sidebar(ledger)

    st.title("發票對應人員對帳系統")

    render_invoice_details_editor(ledger)
    render_editor(ledger)
    render_summary(ledger)

    left, right = st.columns([3, 1])
    with left:
        render_pie_charts(ledger)
    with right:
        render_total(ledger)


if __name__ == "__main__":
    main()
