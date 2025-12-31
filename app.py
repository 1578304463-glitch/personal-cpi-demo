import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Personal CPI Demo (V0)", layout="wide")

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CPI = APP_DIR / "official_cpi_mom_2024-11_2025-11_long.csv"

# ----------------------------
# Helpers
# ----------------------------
def read_csv_upload(uploaded_file, encodings=("gb18030", "utf-8-sig", "utf-8")) -> pd.DataFrame:
    """Read uploaded CSV with common encodings."""
    data = uploaded_file.getvalue()
    for enc in encodings:
        try:
            return pd.read_csv(pd.io.common.BytesIO(data), encoding=enc)
        except Exception:
            continue
    # last resort
    return pd.read_csv(pd.io.common.BytesIO(data))

def read_official_cpi_default(path: Path) -> pd.DataFrame:
    """Read bundled official CPI long table."""
    if not path.exists():
        raise FileNotFoundError(
            f"未找到官方CPI文件：{path.name}。请确认它已在仓库根目录，并随应用一起部署。"
        )
    # we exported as utf-8-sig
    return pd.read_csv(path, encoding="utf-8-sig")

def clean_bill_v0(df: pd.DataFrame) -> pd.DataFrame:
    """
    V0 清洗：兼容“最小三列”思路，但暂时先按你测试账单格式（time/merchant/amount）做默认。
    如果老师上传列名不同，先提示用户稍后将加入字段映射。
    """
    df = df.copy()

    needed = {"time", "merchant", "amount"}
    if not needed.issubset(set(df.columns)):
        return df  # 原样返回，让页面提示

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["time", "amount"])

    # 支出统一为正数
    df["amount"] = df["amount"].abs()

    # month: YYYY-MM
    df["month"] = df["time"].dt.to_period("M").astype(str)

    # merchant as string
    df["merchant"] = df["merchant"].astype(str)

    return df

# ----------------------------
# UI
# ----------------------------
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择页面",
    ["Page 1 上传与清洗（V0）", "Page 2 分类与权重（占位）", "Page 3 年度总结（占位）"],
)

if page == "Page 1 上传与清洗（V0）":
    st.title("Page 1 上传与清洗（V0）")
    st.caption("上线版：请上传账单 CSV。官方 CPI 长表默认已内置（也可选择手动上传）。")

    colA, colB = st.columns(2)
    with colA:
        bill_up = st.file_uploader(
            "上传账单 CSV（必选）",
            type=["csv"],
            help="需包含日期、金额（支出）、摘要/商户名。V0 默认识别列名 time/merchant/amount。",
        )
    with colB:
        cpi_up = st.file_uploader(
            "可选：上传官方 CPI 长表 CSV（不传则使用内置文件）",
            type=["csv"],
            help="字段需包含 month, category, mom_index。",
        )

    # 必须上传账单
    if bill_up is None:
        st.warning("请先上传一份账单 CSV（包含日期、金额、摘要/商户名）。上传后将自动生成个人 CPI 年度报告。")
        st.stop()

    # 读账单（兼容常见编码）
    try:
        bill_raw = read_csv_upload(bill_up)
    except Exception as e:
        st.error(f"账单 CSV 读取失败：{e}")
        st.stop()

    # 读官方 CPI
    try:
        if cpi_up is not None:
            cpi = read_csv_upload(cpi_up, encodings=("utf-8-sig", "utf-8", "gb18030"))
            cpi_source = "上传文件"
        else:
            cpi = read_official_cpi_default(DEFAULT_CPI)
            cpi_source = f"内置文件：{DEFAULT_CPI.name}"
    except Exception as e:
        st.error(f"官方 CPI 数据读取失败：{e}")
        st.stop()

    st.success(f"账单来源：上传文件；官方 CPI 来源：{cpi_source}")

    # 清洗账单
    bill = clean_bill_v0(bill_raw)

    st.subheader("数据检查")
    c1, c2, c3 = st.columns(3)

    # 时间覆盖
    if "time" in bill.columns and bill["time"].notna().any():
        start = bill["time"].min().date()
        end = bill["time"].max().date()
        months = bill["month"].nunique() if "month" in bill.columns else 0
        c1.metric("时间覆盖", f"{start} → {end}", f"{months}个月")
    else:
        c1.metric("时间覆盖", "未解析", "V0 默认识别列名 time/merchant/amount")

    # 样本规模
    if "amount" in bill.columns and pd.api.types.is_numeric_dtype(bill["amount"]):
        total = float(bill["amount"].sum())
        c2.metric("样本规模", f"{len(bill):,} 笔", f"总支出 {total:,.2f}")
    else:
        c2.metric("样本规模", "未解析", "请检查金额列")

    # 数据质量
    bad_rows = max(len(bill_raw) - len(bill), 0)
    c3.metric("数据质量", "已清洗完成", f"剔除/无法解析 {bad_rows} 行")

    # 预览
    st.subheader("账单预览（清洗后前10行）")
    st.dataframe(bill.head(10), use_container_width=True)

    st.subheader("官方 CPI 长表检查（前10行）")
    st.write(f"记录数：{len(cpi):,}；字段：{list(cpi.columns)}")
    st.dataframe(cpi.head(10), use_container_width=True)

    # V0 重要提示
    if not {"time", "merchant", "amount"}.issubset(set(bill.columns)):
        st.warning(
            "你的账单列名不是 V0 默认的 time/merchant/amount。"
            "下一步我们会加入“字段映射下拉框”，让任意列名都能跑通。"
        )

elif page == "Page 2 分类与权重（占位）":
    st.title("Page 2 分类与权重（占位）")
    st.info("下一步接入：规则分类字典V1 → 覆盖率卡片 → 饼图与排序表（金额/占比/笔数）。")

elif page == "Page 3 年度总结（占位）":
    st.title("Page 3 年度总结（占位）")
    st.info("下一步接入：动态权重 + 官方分项指数 → 个人 CPI 曲线、CumGap、Top3 贡献、年度关键词与年度总结文案。")
