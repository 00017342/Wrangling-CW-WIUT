import streamlit as st
import pandas as pd
import plotly.express as px
import json
import io
from datetime import datetime

st.set_page_config(layout="wide")

_DEFAULTS = {
    "df": None,
    "history": [],
    "logs": [],
    "transformation_count": 0,
    "validation_violations": 0,
    "widget_gen": 0,
    "toast": None,
    "loaded_file_key": None,
    "last_result": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

@st.cache_data(show_spinner=False)
def _detect_datetime_cols(df: pd.DataFrame) -> list:
    """Return columns whose values parse as datetimes in >80 % of rows."""
    result = []
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                conv = pd.to_datetime(df[col], format="mixed", errors="coerce")
                if len(df[col]) > 0 and conv.notna().sum() / len(df[col]) > 0.8:
                    result.append(col)
            except Exception:
                pass
    return result


@st.cache_data(show_spinner=False)
def _missing_per_col(df: pd.DataFrame) -> pd.Series:
    return df.isnull().sum()


@st.cache_data(show_spinner=False)
def _count_duplicates(df: pd.DataFrame, subset, keep) -> int:
    """Count duplicate rows.  subset must be a tuple (hashable) or None."""
    subset_list = list(subset) if subset else None
    return int(df.duplicated(subset=subset_list, keep=keep).sum())


@st.cache_data(show_spinner=False)
def _dup_preview(df: pd.DataFrame, subset, keep) -> pd.DataFrame:
    """Return first 20 rows that would be removed/marked as duplicate."""
    subset_list = list(subset) if subset else None
    mask = df.duplicated(subset=subset_list, keep=keep)
    return df[mask].head(20)


def save_snapshot():
    """Push a deep copy of df onto the undo stack."""
    if st.session_state.df is not None:
        st.session_state.history.append(st.session_state.df.copy())


def log_action(action: str, details: dict):
    """Append a structured entry to the transformation log."""
    st.session_state.transformation_count += 1
    st.session_state.logs.append({
        "step":      st.session_state.transformation_count,
        "action":    action,
        "details":   details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def commit(new_df: pd.DataFrame, action: str, details: dict, toast_msg: str,
           result: dict = None):
    """
    Atomically: save snapshot → update df → log → set toast → bump widget_gen
    → store optional result data → trigger rerun.

    Every Apply button must go through this.

    Parameters
    ----------
    result : dict, optional
        {"label": str, "df": pd.DataFrame | None}
        Displayed at the top of the Cleaning Studio on the next render so it
        is actually visible (anything rendered before st.rerun() is discarded).
    """
    save_snapshot()
    st.session_state.df = new_df
    log_action(action, details)
    st.session_state.toast       = {"type": "success", "msg": toast_msg}
    st.session_state.last_result = result  # None clears any previous result
    st.session_state.widget_gen += 1
    st.rerun()


def undo():
    if st.session_state.history:
        st.session_state.df = st.session_state.history.pop()
        if st.session_state.logs:
            st.session_state.logs.pop()
        st.session_state.transformation_count = max(
            0, st.session_state.transformation_count - 1
        )
        st.session_state.widget_gen += 1
        st.session_state.last_result = None
        st.session_state.toast = {"type": "info", "msg": "Last step undone."}
    else:
        st.session_state.toast = {"type": "warning", "msg": "Nothing to undo."}


def reset_all():
    if st.session_state.history:
        st.session_state.df                   = st.session_state.history[0].copy()
        st.session_state.history              = []
        st.session_state.logs                 = []
        st.session_state.transformation_count = 0
        st.session_state.widget_gen          += 1
        st.session_state.last_result          = None
        st.session_state.toast = {"type": "info", "msg": "All transformations reset."}
    else:
        st.session_state.toast = {"type": "warning", "msg": "No history to reset to."}


def show_toast():
    """Render and immediately clear the pending toast message."""
    t = st.session_state.toast
    if t:
        getattr(st, t["type"])(t["msg"])
        st.session_state.toast = None


def show_last_result():
    """
    Display and clear the post-commit result stored in session state.

    Because commit() calls st.rerun(), any st.dataframe() / st.info() calls
    placed *before* commit() inside an Apply handler are abandoned and never
    reach the browser.  Instead, callers pass result={"label":…, "df":…} to
    commit(), which stores it here so it is rendered on the *next* pass.
    """
    r = st.session_state.get("last_result")
    if r:
        if r.get("label"):
            st.caption(r["label"])
        if r.get("df") is not None and not r["df"].empty:
            st.dataframe(r["df"], width="stretch")
        st.session_state.last_result = None


def safe_join(cols):
    return ", ".join(str(c) for c in cols) if cols else "None"


def build_log_summary(details: dict) -> str:
    """Turn a details dict into a short human-readable one-liner."""
    parts = []
    if details.get("columns"):
        parts.append("cols: " + ", ".join(str(c) for c in details["columns"]))
    if details.get("action"):
        parts.append(str(details["action"]))
    if details.get("rows_affected") is not None:
        parts.append(f"{details['rows_affected']} rows affected")
    if details.get("rows_removed"):
        parts.append(f"{details['rows_removed']} rows removed")
    if details.get("rows_changed"):
        parts.append(f"{details['rows_changed']} rows changed")
    if details.get("values_capped"):
        parts.append(f"{details['values_capped']} values capped")
    if details.get("mapping"):
        parts.append(f"{len(details['mapping'])} columns renamed")
    if details.get("new_column"):
        parts.append(f"new col: {details['new_column']}")
    if details.get("method"):
        parts.append(str(details["method"]))
    if details.get("type"):
        parts.append(str(details["type"]))
    return " · ".join(parts) if parts else "—"


def show_violations(vdf: pd.DataFrame, dl_key: str):
    """
    Display validation violations and update the counter.
    Moved to module level so it is not redefined on every render.
    """
    n = len(vdf)
    st.session_state.validation_violations = n
    if n == 0:
        st.success("No violations found — all values pass the constraint")
    else:
        st.warning(f"{n} violation(s) found")
        st.dataframe(vdf.head(50), width="stretch")
        st.download_button(
            "Download violations as CSV",
            data=vdf.to_csv(index=False).encode("utf-8"),
            file_name="violations.csv",
            mime="text/csv",
            key=dl_key,
        )


with st.sidebar:
    _, mainContent, _ = st.columns([0.5, 2, 0.5])
    with mainContent:
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            label="Upload file",
            type=["csv", "xlsx", "xlsm", "xlsb", "xltx", "xltm", "xls"],
        )

        if uploaded_file is not None:
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"

            if st.session_state.loaded_file_key != file_key:
                try:
                    if uploaded_file.name.endswith(".csv"):
                        loaded = pd.read_csv(uploaded_file)
                    else:
                        loaded = pd.read_excel(uploaded_file)

                    for col in loaded.columns:
                        try:
                            loaded[col] = pd.to_numeric(loaded[col])
                        except (ValueError, TypeError):
                            pass

                    st.session_state.df                   = loaded
                    st.session_state.history              = [loaded.copy()]
                    st.session_state.logs                 = []
                    st.session_state.transformation_count = 0
                    st.session_state.widget_gen           = 0
                    st.session_state.toast                = None
                    st.session_state.last_result          = None
                    st.session_state.loaded_file_key      = file_key
                except Exception as e:
                    st.error(f"Failed to load file: {e}")

        st.divider()
        st.write("**Workflow**")
        if st.button("Undo Last Step", width="stretch"):
            undo()
            st.rerun()
        if st.button("Reset Session", width="stretch"):
            reset_all()
            st.rerun()

        st.divider()
        st.write("**Logs**")
        if st.session_state.logs:
            for entry in reversed(st.session_state.logs[-5:]):
                st.caption(f"[{entry['timestamp']}] {entry['action']}")
        else:
            st.caption("No transformations yet.")


overviewTab, cleaningStudioTab, visualizationTab, exportReportTab = st.tabs(
    ["Overview", "Cleaning Studio", "Visualization", "Export & Report"]
)


with overviewTab:
    df = st.session_state.df

    st.header("Dataset Overview")
    st.write("Here you can explore uploaded dataset metrics")

    if df is not None:
        rows, columns = df.shape
        column_names  = df.columns.tolist()
        numeric_cols  = df.select_dtypes(include="number").columns.tolist()
        cat_cols_raw  = df.select_dtypes(include=["object", "category"]).columns.tolist()

        datetime_columns      = _detect_datetime_cols(df)
        categorical_cols      = [c for c in cat_cols_raw if c not in datetime_columns]
        numeric_columns       = len(numeric_cols)
        categorical_columns   = len(categorical_cols)
        datetime_column_count = len(datetime_columns)
    else:
        rows = columns = 0
        column_names = numeric_cols = categorical_cols = datetime_columns = []
        numeric_columns = categorical_columns = datetime_column_count = 0

    rowsCol, colsCol, numCol, catCol, dtCol = st.columns(5)
    with rowsCol:   st.metric("Rows",        f"{rows:,}")
    with colsCol:   st.metric("Columns",     columns)
    with numCol:    st.metric("Numeric",     numeric_columns)
    with catCol:    st.metric("Categorical", categorical_columns)
    with dtCol:     st.metric("Datetime",    datetime_column_count)

    st.divider()
    if df is not None:
        st.subheader("Column Names")
        st.write(safe_join(column_names))

    st.divider()
    st.header("Data Profiling")

    datatypesCol, mvCol = st.columns(2)

    with datatypesCol:
        st.subheader("Data Types")
        if df is not None:
            st.write(f"Numeric columns ({numeric_columns}): {safe_join(numeric_cols)}")
            st.write(f"Categorical columns ({categorical_columns}): {safe_join(categorical_cols)}")
            st.write(f"Datetime columns ({datetime_column_count}): {safe_join(datetime_columns)}")
        else:
            st.info("No dataset loaded")

    with mvCol:
        st.subheader("Missing Values")
        if df is not None:
            missing_per_column = _missing_per_col(df)
            total_missing      = int(missing_per_column.sum())
            st.write(f"Total missing values: **{total_missing}**")
            missing_columns    = missing_per_column[missing_per_column > 0]
            if missing_columns.empty:
                st.success("No missing values found")
            else:
                st.dataframe(
                    missing_columns.rename("missing_count")
                        .reset_index()
                        .rename(columns={"index": "column"}),
                    width="stretch",
                )
        else:
            st.info("No dataset loaded")

    st.divider()
    dupCol, previewCol = st.columns(2)

    with dupCol:
        st.subheader("Duplicates")
        if df is not None:
            duplicate_count = _count_duplicates(df, None, "first")
            st.write(f"Total duplicate rows: **{duplicate_count}**")
            if duplicate_count > 0:
                if st.button("Remove Duplicates", key="overview_remove_dup"):
                    new_df  = df.drop_duplicates()
                    removed = len(df) - len(new_df)
                    commit(new_df, "Remove Duplicates",
                           {"rows_removed": removed},
                           f"Removed {removed} duplicate rows")
        else:
            st.info("No dataset loaded")

    with previewCol:
        st.subheader("Data Preview (first 10 rows)")
        if df is not None:
            st.dataframe(df.head(10), width="stretch")
        else:
            st.info("No dataset loaded")


with cleaningStudioTab:
    st.header("Cleaning Studio")
    st.write("Clean, transform, and prepare your dataset with different options")

    if st.session_state.df is None:
        st.info("Upload a dataset first")
    else:
        df  = st.session_state.df
        gen = st.session_state.widget_gen   # short alias for all widget keys

        mainColumn, metricsColumn = st.columns([4, 4])

        with mainColumn:
            show_toast()
            show_last_result()

            with st.expander("Missing values", key="exp_mv"):
                selected_cols = st.multiselect(
                    "Columns", df.columns.tolist(), key=f"mv_cols_{gen}"
                )

                if not selected_cols:
                    st.warning("Select at least one column")
                else:
                    missing_counts = _missing_per_col(df)[selected_cols]
                    nonzero = missing_counts[missing_counts > 0]
                    if not nonzero.empty:
                        st.dataframe(
                            nonzero.rename("missing")
                                .reset_index()
                                .rename(columns={"index": "column"})
                        )
                    else:
                        st.success("No missing values in selected columns")

                    action = st.selectbox(
                        "Action",
                        ["Drop rows", "Fill numeric with median", "Fill numeric with mean",
                         "Fill categorical with mode", "Fill with custom value"],
                        key=f"mv_action_{gen}",
                    )

                    custom_value = None
                    if action == "Fill with custom value":
                        custom_value = st.text_input("Custom value", key=f"mv_custom_{gen}")

                    if st.button("Apply", key=f"mv_apply_{gen}"):
                        new_df = df.copy()

                        if action == "Drop rows":
                            before        = len(new_df)
                            new_df        = new_df.dropna(subset=selected_cols)
                            rows_affected = before - len(new_df)
                        else:
                            rows_affected = 0
                            for col in selected_cols:
                                mask  = new_df[col].isna()
                                count = int(mask.sum())
                                if count == 0:
                                    continue
                                if action == "Fill numeric with median" and pd.api.types.is_numeric_dtype(new_df[col]):
                                    new_df.loc[mask, col] = new_df[col].median()
                                elif action == "Fill numeric with mean" and pd.api.types.is_numeric_dtype(new_df[col]):
                                    new_df.loc[mask, col] = new_df[col].mean()
                                elif action == "Fill categorical with mode" and not pd.api.types.is_numeric_dtype(new_df[col]):
                                    mode_val = new_df[col].mode(dropna=True)
                                    if not mode_val.empty:
                                        new_df.loc[mask, col] = mode_val.iloc[0]
                                elif action == "Fill with custom value":
                                    new_df.loc[mask, col] = custom_value
                                rows_affected += count

                        commit(
                            new_df, "Missing Values",
                            {"action": action, "columns": selected_cols, "rows_affected": rows_affected},
                            f"Missing values handled — {rows_affected} cell(s) filled/dropped "
                            f"across {len(selected_cols)} column(s)",
                        )

            with st.expander("Duplicate handling", key="exp_dup"):
                dup_mode = st.radio(
                    "Check duplicates by",
                    ["All columns", "Selected columns"],
                    key=f"dup_mode_{gen}",
                )

                subset_cols = None
                if dup_mode == "Selected columns":
                    subset_cols = st.multiselect(
                        "Columns", df.columns.tolist(), key=f"dup_subset_{gen}"
                    )
                    if not subset_cols:
                        st.warning("Select at least one column")

                keep_option = st.selectbox(
                    "Action",
                    ["Keep first", "Keep last", "Remove all duplicates"],
                    key=f"dup_keep_{gen}",
                )
                keep_map = {"Keep first": "first", "Keep last": "last",
                            "Remove all duplicates": False}
                keep_val = keep_map[keep_option]

                can_preview = not (dup_mode == "Selected columns" and not subset_cols)
                if can_preview:
                    subset_tuple = tuple(subset_cols) if subset_cols else None
                    keep_arg     = keep_val if keep_val is not False else False
                    dup_count = _count_duplicates(df, subset_tuple, keep_arg)
                    st.write(f"Duplicate rows found: **{dup_count}**")
                    if dup_count > 0:
                        st.caption("Preview (first 20 duplicate rows)")
                        st.dataframe(_dup_preview(df, subset_tuple, keep_arg))

                if st.button("Apply", key=f"dup_apply_{gen}"):
                    if dup_mode == "Selected columns" and not subset_cols:
                        st.warning("Select at least one column")
                    else:
                        before  = len(df)
                        s_list  = list(subset_cols) if subset_cols else None
                        if keep_val is False:
                            new_df = df[~df.duplicated(subset=s_list, keep=False)].copy()
                        else:
                            new_df = df.drop_duplicates(subset=s_list, keep=keep_val).copy()
                        rows_removed = before - len(new_df)
                        commit(
                            new_df, "Duplicate Handling",
                            {"action": keep_option, "rows_removed": rows_removed},
                            f"Removed {rows_removed} duplicate row(s)",
                        )

            with st.expander("Data type conversion", key="exp_dtype"):
                st.subheader("Data type conversion")

                selected_cols = st.multiselect(
                    "Select columns", df.columns.tolist(), key=f"dtype_cols_{gen}"
                )

                if not selected_cols:
                    st.warning("Select at least one column")
                else:
                    conversion_type = st.selectbox(
                        "Conversion type",
                        ["To numeric", "To categorical", "To datetime"],
                        key=f"dtype_conv_{gen}",
                    )

                    datetime_format = None
                    clean_numeric   = False

                    if conversion_type == "To datetime":
                        datetime_format = st.text_input(
                            "Datetime format (optional, e.g. %Y-%m-%d)",
                            key=f"dtype_dtfmt_{gen}",
                        )
                    if conversion_type == "To numeric":
                        clean_numeric = st.checkbox(
                            "Clean numeric strings (remove commas, currency symbols)",
                            key=f"dtype_clean_{gen}",
                        )

                    if st.button("Apply", key=f"dtype_apply_{gen}"):
                        new_df            = df.copy()
                        total_changed     = 0
                        total_errors      = 0
                        processed_columns = 0
                        per_col_warnings  = []

                        for col in selected_cols:
                            orig_series = new_df[col]
                            try:
                                before_na = int(orig_series.isna().sum())

                                if conversion_type == "To numeric":
                                    series = orig_series
                                    if clean_numeric:
                                        series = (orig_series.astype(str)
                                                  .str.replace(r"[,\$\€\£]", "", regex=True)
                                                  .str.replace(r"\s+", "", regex=True))
                                    converted = pd.to_numeric(series, errors="coerce")

                                elif conversion_type == "To datetime":
                                    fmt       = datetime_format if datetime_format else "mixed"
                                    converted = pd.to_datetime(orig_series, format=fmt, errors="coerce")

                                else:
                                    converted = orig_series.astype("category")

                                after_na   = int(converted.isna().sum())
                                newly_null = max(after_na - before_na, 0)
                                total_errors  += newly_null
                                total_changed += max(
                                    (len(orig_series) - after_na) - (len(orig_series) - before_na), 0
                                )
                                new_df[col]        = converted
                                processed_columns += 1

                                if newly_null:
                                    per_col_warnings.append(
                                        f"'{col}': {newly_null} value(s) could not be converted → set to NaN"
                                    )

                            except Exception as e:
                                total_errors += 1
                                per_col_warnings.append(f"'{col}': {e}")

                        result_data = None
                        if per_col_warnings:
                            warn_df     = pd.DataFrame({"warning": per_col_warnings})
                            result_data = {"label": "Conversion warnings:", "df": warn_df}

                        commit(
                            new_df, "Data Type Conversion",
                            {"type": conversion_type, "columns": selected_cols,
                             "rows_changed": total_changed, "errors": total_errors},
                            f"Converted {processed_columns} column(s) to {conversion_type.lower()}"
                            + (f" — {total_errors} coercion error(s)" if total_errors else ""),
                            result=result_data,
                        )

            with st.expander("Categorical cleaning", key="exp_cat"):
                st.subheader("Categorical cleaning")

                selected_cols = st.multiselect(
                    "Select categorical columns", df.columns.tolist(), key=f"cat_cols_{gen}"
                )

                if not selected_cols:
                    st.warning("Select at least one column")
                else:
                    st.subheader("Basic cleaning")
                    trim_whitespace = st.checkbox("Trim whitespace",       key=f"cat_trim_{gen}")
                    to_lower        = st.checkbox("Convert to lowercase",  key=f"cat_lower_{gen}")
                    to_title        = st.checkbox("Convert to title case", key=f"cat_title_{gen}")

                    invalid_case = to_lower and to_title
                    if invalid_case:
                        st.error("Choose either lowercase OR title case — not both")

                    st.subheader("Value mapping")
                    enable_mapping = st.checkbox("Enable mapping", key=f"cat_map_en_{gen}")

                    mapping_df          = None
                    set_unmatched_other = False
                    other_value         = "Other"

                    if enable_mapping:
                        all_unique = pd.Series(dtype="object")
                        for col in selected_cols:
                            all_unique = pd.concat([all_unique, df[col].dropna().astype(str)])
                        all_unique = (pd.Series(all_unique.unique())
                                      .sort_values().reset_index(drop=True))

                        mapping_df = pd.DataFrame({
                            "old_value": all_unique,
                            "new_value": all_unique,
                        })
                        mapping_df = st.data_editor(
                            mapping_df, num_rows="dynamic", key=f"cat_mapping_editor_{gen}"
                        )

                        if mapping_df["old_value"].duplicated().any():
                            st.error("Duplicate 'old_value' entries in mapping table")
                        if mapping_df["new_value"].isna().any():
                            st.warning("Some new_value cells are empty")

                        set_unmatched_other = st.checkbox(
                            "Set unmatched values to 'Other'", key=f"cat_unmatched_{gen}"
                        )
                        if set_unmatched_other:
                            other_value = st.text_input(
                                "Other value label", value="Other", key=f"cat_other_val_{gen}"
                            )

                    st.subheader("Rare category grouping")
                    enable_rare = st.checkbox("Enable rare category grouping", key=f"cat_rare_en_{gen}")

                    rare_threshold = 0.05
                    rare_label     = "Other"
                    if enable_rare:
                        rare_threshold = st.slider(
                            "Threshold (proportion)", 0.0, 1.0, 0.05, 0.01, key=f"cat_rare_thresh_{gen}"
                        )
                        rare_label = st.text_input(
                            "Rare category label", value="Other", key=f"cat_rare_label_{gen}"
                        )

                    st.subheader("Encoding")
                    one_hot = st.checkbox("Apply one-hot encoding", key=f"cat_ohe_{gen}")

                    if st.button("Apply", key=f"cat_clean_apply_{gen}"):
                        if invalid_case:
                            st.error("Fix the lowercase / title case conflict first")
                        else:
                            new_df                 = df.copy()
                            total_rows_affected    = 0
                            total_columns_affected = 0

                            mapping_dict = None
                            if enable_mapping and mapping_df is not None:
                                mapping_dict = dict(zip(
                                    mapping_df["old_value"].astype(str),
                                    mapping_df["new_value"].astype(str),
                                ))

                            for col in selected_cols:
                                try:
                                    original_values = new_df[col].copy()
                                    result_series   = new_df[col].astype(object).copy()
                                    not_null_mask   = result_series.notna()
                                    working         = result_series[not_null_mask].astype(str)

                                    if trim_whitespace:
                                        working = working.str.strip()
                                    if to_lower:
                                        working = working.str.lower()
                                    if to_title:
                                        working = working.str.title()

                                    if mapping_dict is not None:
                                        mapped  = working.map(mapping_dict)
                                        working = (mapped.fillna(other_value)
                                                   if set_unmatched_other
                                                   else mapped.where(mapped.notna(), working))

                                    if enable_rare:
                                        freq        = working.value_counts(normalize=True)
                                        rare_values = freq[freq < rare_threshold].index
                                        working     = working.where(
                                            ~working.isin(rare_values), rare_label
                                        )

                                    result_series[not_null_mask] = working.values
                                    new_df[col] = result_series

                                    rows_changed = int(
                                        (original_values.fillna("__NA__").astype(str)
                                         != new_df[col].fillna("__NA__").astype(str)).sum()
                                    )
                                    if rows_changed > 0:
                                        total_rows_affected    += rows_changed
                                        total_columns_affected += 1

                                except Exception as e:
                                    st.warning(f"Error on column '{col}': {e}")

                            if one_hot:
                                try:
                                    ohe_cols = [c for c in selected_cols if c in new_df.columns]
                                    new_df   = pd.get_dummies(new_df, columns=ohe_cols)
                                    total_columns_affected += len(ohe_cols)
                                except Exception as e:
                                    st.warning(f"One-hot encoding failed: {e}")

                            commit(
                                new_df, "Categorical Cleaning",
                                {"columns": selected_cols,
                                 "rows_affected": total_rows_affected,
                                 "columns_affected": total_columns_affected},
                                f"Categorical cleaning applied — {total_rows_affected} cell(s) changed "
                                f"across {total_columns_affected} column(s)",
                            )

            with st.expander("Outlier handling", key="exp_outlier"):
                st.subheader("Outlier handling")

                numeric_cols_outlier = df.select_dtypes(include=["number"]).columns.tolist()

                if not numeric_cols_outlier:
                    st.warning("No numeric columns available")
                else:
                    selected_cols = st.multiselect(
                        "Select numeric columns",
                        numeric_cols_outlier, key=f"outlier_cols_{gen}"
                    )

                    if not selected_cols:
                        st.warning("Select at least one column")
                    else:
                        action  = st.selectbox(
                            "Action", ["Show only", "Cap (Winsorize)", "Remove rows"],
                            key=f"outlier_action_{gen}",
                        )
                        lower_q = st.slider(
                            "Lower quantile", 0.0, 0.5, 0.05, 0.01, key=f"outlier_lq_{gen}"
                        )
                        upper_q = st.slider(
                            "Upper quantile", 0.5, 1.0, 0.95, 0.01, key=f"outlier_uq_{gen}"
                        )

                        if st.button("Apply", key=f"outlier_apply_{gen}"):
                            new_df         = df.copy()
                            summary        = []
                            total_outliers = 0
                            total_capped   = 0
                            skipped_cols   = []

                            for col in selected_cols:
                                try:
                                    series = new_df[col]
                                    if series.isna().all():
                                        skipped_cols.append(col)
                                        continue
                                    q1, q3 = series.quantile(0.25), series.quantile(0.75)
                                    iqr    = q3 - q1
                                    lo_iqr = q1 - 1.5 * iqr
                                    hi_iqr = q3 + 1.5 * iqr
                                    mask   = (series < lo_iqr) | (series > hi_iqr)
                                    count  = int(mask.sum())
                                    total_outliers += count

                                    col_info = {
                                        "column":   col,
                                        "outliers": count,
                                        "min":      round(float(series.min()), 4),
                                        "max":      round(float(series.max()), 4),
                                    }
                                    if action == "Cap (Winsorize)":
                                        lo_cap  = series.quantile(lower_q)
                                        hi_cap  = series.quantile(upper_q)
                                        capped  = series.clip(lower=lo_cap, upper=hi_cap)
                                        changed = int((series != capped).sum())
                                        total_capped  += changed
                                        new_df[col]    = capped
                                        col_info["capped"] = changed
                                    summary.append(col_info)
                                except Exception as e:
                                    skipped_cols.append(f"{col} ({e})")

                            total_removed = 0
                            if action == "Remove rows":
                                combined = pd.Series(False, index=new_df.index)
                                for col in selected_cols:
                                    try:
                                        s   = new_df[col]
                                        q1, q3 = s.quantile(0.25), s.quantile(0.75)
                                        iqr = q3 - q1
                                        combined |= (s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)
                                    except Exception:
                                        pass
                                before        = len(new_df)
                                new_df        = new_df[~combined]
                                total_removed = before - len(new_df)

                            if action == "Show only":
                                if summary:
                                    st.dataframe(pd.DataFrame(summary))
                                if skipped_cols:
                                    st.warning("Skipped: " + ", ".join(skipped_cols))
                                st.info(
                                    f"Detected {total_outliers} outlier value(s) across "
                                    f"{len(summary)} column(s) — no changes made"
                                )
                            else:
                                msg = (
                                    f"Outlier capping applied — {total_capped} value(s) capped"
                                    if action == "Cap (Winsorize)"
                                    else f"Outlier rows removed — {total_removed} row(s) dropped"
                                )
                                result_data = (
                                    {"label": "Outlier summary (per column):",
                                     "df": pd.DataFrame(summary)}
                                    if summary else None
                                )
                                commit(
                                    new_df, "Outlier Handling",
                                    {"action": action, "columns": selected_cols,
                                     "total_outliers": total_outliers,
                                     "rows_removed":   total_removed,
                                     "values_capped":  total_capped},
                                    msg,
                                    result=result_data,
                                )

            with st.expander("Scaling", key="exp_scaling"):
                st.subheader("Scaling")

                numeric_cols_scaling = df.select_dtypes(include=["number"]).columns.tolist()

                if not numeric_cols_scaling:
                    st.warning("No numeric columns available")
                else:
                    selected_cols = st.multiselect(
                        "Select numeric columns", numeric_cols_scaling, key=f"scaling_cols_{gen}"
                    )

                    if not selected_cols:
                        st.warning("Select at least one column")
                    else:
                        method = st.selectbox(
                            "Scaling method",
                            ["Min-Max Scaling", "Z-score Standardization"],
                            key=f"scaling_method_{gen}",
                        )

                        if st.button("Apply", key=f"scaling_apply_{gen}"):
                            new_df       = df.copy()
                            stats_output = []
                            skipped      = []

                            for col in selected_cols:
                                try:
                                    series = new_df[col]
                                    if series.isna().all():
                                        skipped.append(f"{col} (all NaN)")
                                        continue

                                    before = {k: float(getattr(series, k)())
                                              for k in ("mean", "std", "min", "max")}

                                    if method == "Min-Max Scaling":
                                        lo, hi = series.min(), series.max()
                                        if lo == hi:
                                            skipped.append(f"{col} (constant)")
                                            continue
                                        scaled = (series - lo) / (hi - lo)
                                    else:
                                        m, s = series.mean(), series.std()
                                        if s == 0:
                                            skipped.append(f"{col} (zero std)")
                                            continue
                                        scaled = (series - m) / s

                                    new_df[col] = scaled
                                    stats_output.append({
                                        "column":      col,
                                        "before_mean": round(before["mean"], 4),
                                        "after_mean":  round(float(scaled.mean()), 4),
                                        "before_std":  round(before["std"],  4),
                                        "after_std":   round(float(scaled.std()),  4),
                                        "before_min":  round(before["min"],  4),
                                        "after_min":   round(float(scaled.min()),  4),
                                        "before_max":  round(before["max"],  4),
                                        "after_max":   round(float(scaled.max()),  4),
                                    })
                                except Exception as e:
                                    skipped.append(f"{col} ({e})")

                            if not stats_output:
                                st.error(
                                    "No columns were scaled — " +
                                    (("skipped: " + ", ".join(skipped)) if skipped else "unknown error")
                                )
                            else:
                                label = f"Scaling stats — {method}"
                                if skipped:
                                    label += f"  |  Skipped: {', '.join(skipped)}"
                                commit(
                                    new_df, "Scaling",
                                    {"method": method, "columns": selected_cols},
                                    f"{method} applied to {len(stats_output)} column(s)"
                                    + (f" — {len(skipped)} skipped" if skipped else ""),
                                    result={"label": label, "df": pd.DataFrame(stats_output)},
                                )

            with st.expander("Column operations", key="exp_colops"):
                st.subheader("Column operations")

                operation = st.selectbox(
                    "Select operation",
                    ["Rename column", "Drop columns", "Create column (formula)",
                     "Binning (equal width)", "Binning (quantile)"],
                    key=f"colops_operation_{gen}",
                )

                if operation == "Rename column":
                    current_cols = df.columns.tolist()
                    st.caption("Pick a column, type the new name, click Rename.")

                    with st.form(key=f"rename_form_{gen}"):
                        rename_target = st.selectbox(
                            "Column to rename", current_cols,
                            key=f"rename_form_target_{gen}",
                        )
                        rename_new = st.text_input(
                            "New name",
                            placeholder="Type new column name here…",
                            key=f"rename_form_newname_{gen}",
                        )
                        rename_submitted = st.form_submit_button("Rename")

                    if rename_submitted:
                        rename_new_clean = (rename_new or "").strip()
                        if not rename_new_clean:
                            st.error("New name cannot be empty.")
                        elif rename_new_clean == rename_target:
                            st.warning("New name is the same as the current name — nothing changed.")
                        elif rename_new_clean in current_cols:
                            st.error(f"A column named '{rename_new_clean}' already exists.")
                        else:
                            new_df = df.rename(columns={rename_target: rename_new_clean})
                            commit(
                                new_df, "Rename Column",
                                {"mapping": {rename_target: rename_new_clean}},
                                f"Renamed '{rename_target}' → '{rename_new_clean}'",
                            )

                elif operation == "Drop columns":
                    st.caption("Select one or more columns to permanently remove.")

                    with st.form(key=f"drop_form_{gen}"):
                        drop_cols = st.multiselect(
                            "Columns to drop", df.columns.tolist(),
                            key=f"drop_form_cols_{gen}",
                        )
                        if drop_cols:
                            st.warning(
                                f"This will permanently remove {len(drop_cols)} column(s): "
                                f"{safe_join(drop_cols)}"
                            )
                        drop_submitted = st.form_submit_button("Drop selected columns")

                    if drop_submitted:
                        if not drop_cols:
                            st.warning("No columns selected — nothing changed.")
                        else:
                            new_df = df.drop(columns=drop_cols)
                            commit(
                                new_df, "Drop Columns",
                                {"columns": drop_cols},
                                f"Dropped {len(drop_cols)} column(s): {safe_join(drop_cols)}",
                            )

                elif operation == "Create column (formula)":
                    st.caption(
                        "All existing column names are available as variables. "
                        "Supported operators: +  −  *  /  **  %"
                    )

                    with st.form(key=f"formula_form_{gen}"):
                        formula_col_name = st.text_input(
                            "New column name", placeholder="e.g. profit_margin",
                            key=f"formula_form_colname_{gen}",
                        )
                        formula_expr = st.text_input(
                            "Formula", placeholder="e.g. revenue - cost",
                            key=f"formula_form_expr_{gen}",
                        )
                        formula_submitted = st.form_submit_button("Create column")

                    if formula_submitted:
                        err_msg        = None
                        new_df         = None
                        col_name_clean = (formula_col_name or "").strip()
                        expr_clean     = (formula_expr or "").strip()

                        if not col_name_clean:
                            err_msg = "New column name cannot be empty."
                        elif col_name_clean in df.columns:
                            err_msg = f"Column '{col_name_clean}' already exists."
                        elif not expr_clean:
                            err_msg = "Formula cannot be empty."
                        else:
                            try:
                                tmp = df.copy()
                                env = {c: tmp[c] for c in tmp.columns}
                                tmp[col_name_clean] = eval(
                                    expr_clean, {"__builtins__": {}}, env
                                )
                                new_df = tmp
                            except Exception as exc:
                                err_msg = str(exc)

                        if err_msg:
                            st.error(f"Error: {err_msg}")
                        else:
                            commit(
                                new_df, "Create Column",
                                {"new_column": col_name_clean, "formula": expr_clean},
                                f"Column '{col_name_clean}' created",
                            )

                elif operation == "Binning (equal width)":
                    numeric_cols_bin = df.select_dtypes(include="number").columns.tolist()

                    if not numeric_cols_bin:
                        st.warning("No numeric columns available for binning.")
                    else:
                        with st.form(key=f"bin_eq_form_{gen}"):
                            bin_eq_col = st.selectbox(
                                "Source column (numeric only)", numeric_cols_bin,
                                key=f"bin_eq_form_col_{gen}",
                            )
                            bin_eq_n = st.number_input(
                                "Number of bins", min_value=2, max_value=100, value=5,
                                key=f"bin_eq_form_n_{gen}",
                            )
                            bin_eq_newcol = st.text_input(
                                "New column name", placeholder="e.g. age_group",
                                key=f"bin_eq_form_newcol_{gen}",
                            )
                            bin_eq_submitted = st.form_submit_button("Apply binning")

                        if bin_eq_submitted:
                            err_msg      = None
                            new_df       = None
                            newcol_clean = (bin_eq_newcol or "").strip()

                            if not newcol_clean:
                                err_msg = "New column name cannot be empty."
                            elif newcol_clean in df.columns:
                                err_msg = f"Column '{newcol_clean}' already exists."
                            else:
                                try:
                                    tmp = df.copy()
                                    tmp[newcol_clean] = pd.cut(
                                        tmp[bin_eq_col], bins=int(bin_eq_n)
                                    ).astype(str)
                                    new_df = tmp
                                except Exception as exc:
                                    err_msg = str(exc)

                            if err_msg:
                                st.error(f"Binning error: {err_msg}")
                            else:
                                commit(
                                    new_df, "Binning (equal width)",
                                    {"column": bin_eq_col, "bins": int(bin_eq_n),
                                     "new_column": newcol_clean},
                                    f"Equal-width binning applied → '{newcol_clean}'",
                                )

                elif operation == "Binning (quantile)":
                    numeric_cols_bin = df.select_dtypes(include="number").columns.tolist()

                    if not numeric_cols_bin:
                        st.warning("No numeric columns available for binning.")
                    else:
                        with st.form(key=f"bin_q_form_{gen}"):
                            bin_q_col = st.selectbox(
                                "Source column (numeric only)", numeric_cols_bin,
                                key=f"bin_q_form_col_{gen}",
                            )
                            bin_q_n = st.number_input(
                                "Number of bins", min_value=2, max_value=100, value=5,
                                key=f"bin_q_form_n_{gen}",
                            )
                            bin_q_newcol = st.text_input(
                                "New column name", placeholder="e.g. income_quartile",
                                key=f"bin_q_form_newcol_{gen}",
                            )
                            bin_q_submitted = st.form_submit_button("Apply binning")

                        if bin_q_submitted:
                            err_msg      = None
                            new_df       = None
                            newcol_clean = (bin_q_newcol or "").strip()

                            if not newcol_clean:
                                err_msg = "New column name cannot be empty."
                            elif newcol_clean in df.columns:
                                err_msg = f"Column '{newcol_clean}' already exists."
                            else:
                                try:
                                    tmp = df.copy()
                                    tmp[newcol_clean] = pd.qcut(
                                        tmp[bin_q_col], q=int(bin_q_n), duplicates="drop"
                                    ).astype(str)
                                    new_df = tmp
                                except Exception as exc:
                                    err_msg = str(exc)

                            if err_msg:
                                st.error(f"Binning error: {err_msg}")
                            else:
                                commit(
                                    new_df, "Binning (quantile)",
                                    {"column": bin_q_col, "bins": int(bin_q_n),
                                     "new_column": newcol_clean},
                                    f"Quantile binning applied → '{newcol_clean}'",
                                )

            with st.expander("Data validation", key="exp_validation"):
                st.subheader("Data validation")
                st.caption("Validation reports violations only — it does not modify the dataset.")

                validation_type = st.selectbox(
                    "Validation type",
                    ["Numeric range", "Allowed categories", "Non-null constraint"],
                    key=f"validation_type_{gen}",
                )

                val_df = st.session_state.df

                if validation_type == "Numeric range":
                    v_col = st.selectbox("Column", val_df.columns, key=f"val_col_range_{gen}")
                    v_min = st.number_input("Min allowed value", key=f"val_min_{gen}")
                    v_max = st.number_input("Max allowed value", key=f"val_max_{gen}")

                    if st.button("Validate", key=f"range_validate_{gen}"):
                        if not pd.api.types.is_numeric_dtype(val_df[v_col]):
                            st.error(f"Column '{v_col}' is not numeric")
                        elif v_min > v_max:
                            st.error("Min value cannot be greater than Max value")
                        else:
                            mask = (val_df[v_col] < v_min) | (val_df[v_col] > v_max)
                            show_violations(val_df[mask], f"dl_range_{gen}")

                elif validation_type == "Allowed categories":
                    v_col   = st.selectbox("Column", val_df.columns, key=f"val_col_cat_{gen}")
                    allowed = st.text_input(
                        "Allowed values (comma-separated)", key=f"val_allowed_{gen}"
                    )

                    if st.button("Validate", key=f"cat_validate_{gen}"):
                        allowed_list = [x.strip() for x in allowed.split(",") if x.strip()]
                        if not allowed_list:
                            st.warning("Enter at least one allowed value")
                        else:
                            mask = ~val_df[v_col].astype(str).isin(allowed_list)
                            show_violations(val_df[mask], f"dl_cat_{gen}")

                elif validation_type == "Non-null constraint":
                    v_cols = st.multiselect(
                        "Columns", val_df.columns.tolist(), key=f"val_nonnull_cols_{gen}"
                    )

                    if st.button("Validate", key=f"nonnull_validate_{gen}"):
                        if not v_cols:
                            st.warning("Select at least one column")
                        else:
                            mask = val_df[v_cols].isna().any(axis=1)
                            show_violations(val_df[mask], f"dl_nonnull_{gen}")

        with metricsColumn:
            df_current  = st.session_state.df
            df_original = (st.session_state.history[0]
                           if st.session_state.history else df_current)

            with st.container(border=True):
                st.subheader("Transformation Preview")

                if df_current is not None:
                    orig_rows = df_original.shape[0] if df_original is not None else df_current.shape[0]
                    orig_cols = df_original.shape[1] if df_original is not None else df_current.shape[1]
                    row_delta = df_current.shape[0] - orig_rows
                    col_delta = df_current.shape[1] - orig_cols

                    m1, m2 = st.columns(2)
                    with m1:
                        st.metric(
                            "Current Rows", f"{df_current.shape[0]:,}",
                            delta=f"{row_delta:+,}" if row_delta != 0 else None,
                            delta_color="inverse" if row_delta < 0 else "normal",
                        )
                        st.metric("Transformations Applied", st.session_state.transformation_count)
                    with m2:
                        st.metric(
                            "Current Columns", df_current.shape[1],
                            delta=f"{col_delta:+}" if col_delta != 0 else None,
                        )
                        st.metric(
                            "Validation Violations", st.session_state.validation_violations,
                            delta_color="inverse",
                        )

                    st.divider()
                    q1, q2 = st.columns(2)
                    with q1:
                        st.metric(
                            "Missing Values",
                            f"{int(_missing_per_col(df_current).sum()):,}"
                        )
                    with q2:
                        st.metric(
                            "Duplicate Rows",
                            f"{_count_duplicates(df_current, None, 'first'):,}"
                        )

                else:
                    st.info("No data loaded")

                st.divider()
                btnUndo, btnReset = st.columns(2)
                with btnUndo:
                    if st.button("↩ Undo Last Step", key="clean_undo", width="stretch"):
                        undo()
                        st.rerun()
                with btnReset:
                    if st.button("⟳ Reset All", key="clean_reset", width="stretch"):
                        reset_all()
                        st.rerun()

            with st.container(border=True):
                st.subheader("Transformation Log")
                if st.session_state.logs:
                    st.caption(f"{len(st.session_state.logs)} step(s) recorded")
                    for entry in reversed(st.session_state.logs):
                        summary = build_log_summary(entry["details"])
                        st.markdown(
                            f"""
                            <div style="
                                background: rgba(255,255,255,0.03);
                                border: 1px solid rgba(255,255,255,0.08);
                                border-left: 3px solid #4A90E2;
                                border-radius: 6px;
                                padding: 8px 12px;
                                margin-bottom: 6px;
                            ">
                                <span style="font-size:0.72rem; color:#888;">
                                    Step {entry['step']} &nbsp;·&nbsp; {entry['timestamp']}
                                </span>
                                <div style="font-weight:600; font-size:0.88rem; margin:3px 0 2px 0;">
                                    {entry['action']}
                                </div>
                                <div style="font-size:0.78rem; color:#aaa;">{summary}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No transformations yet — apply a step to see it logged here.")

            with st.container(border=True):
                st.subheader("Current Data Preview")
                if df_current is not None:
                    st.caption(
                        f"Showing first 20 rows · "
                        f"{df_current.shape[0]:,} rows × {df_current.shape[1]} columns total"
                    )
                    st.dataframe(df_current.head(20), width="stretch")
                else:
                    st.info("No data loaded")


with visualizationTab:
    st.header("Visualization")
    st.write("Create interactive charts and explore your dataset visually")

    df = st.session_state.df

    if df is None:
        st.warning("Upload a dataset first")
    else:
        numeric_cols     = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        categorical_cols = [c for c in categorical_cols if df[c].nunique() < len(df) * 0.5]
        all_cols         = df.columns.tolist()

        chartConfigColumn, chartOutputColumn = st.columns([1, 1])

        with chartConfigColumn:
            with st.container(border=True):
                st.subheader("Chart Configuration")

                chart_type = st.selectbox(
                    "Chart Type",
                    ["Histogram", "Box Plot", "Scatter Plot", "Line Chart",
                     "Grouped Bar Chart", "Correlation Heatmap"],
                    key="viz_chart_type",
                )

                x_axis = st.selectbox("X Axis", all_cols, key="viz_x_axis")

                y_axis = None
                if numeric_cols:
                    y_axis = st.selectbox(
                        "Y Axis", ["None"] + numeric_cols, key="viz_y_axis"
                    )
                else:
                    st.warning("No numeric columns for Y axis")

                group_col   = st.selectbox(
                    "Group by (Optional)", ["None"] + categorical_cols, key="viz_group_col"
                )
                aggregation = st.selectbox(
                    "Aggregation method", ["None", "Sum", "Mean", "Count", "Median"],
                    key="viz_aggregation",
                )

                st.subheader("Numeric Filter")
                numeric_filter_col = st.selectbox(
                    "Column", ["None"] + numeric_cols, key="viz_num_filter"
                )
                value_range = None
                if numeric_filter_col != "None":
                    col_min = float(df[numeric_filter_col].min())
                    col_max = float(df[numeric_filter_col].max())
                    if col_min < col_max:
                        value_range = st.slider(
                            "Value Range", col_min, col_max, (col_min, col_max),
                            key="viz_value_range",
                        )

                st.subheader("Categorical Filter")
                cat_filter_col = st.selectbox(
                    "Column", ["None"] + categorical_cols, key="viz_cat_filter"
                )
                selected_categories = []
                if cat_filter_col != "None":
                    unique_vals = df[cat_filter_col].dropna().unique().tolist()
                    selected_categories = st.multiselect(
                        "Selected categories", unique_vals, key="viz_cat_values"
                    )

                genCol, _ = st.columns(2)
                with genCol:
                    generate_chart_btn = st.button("Generate Chart", key="viz_generate")

        with chartOutputColumn:
            with st.container(border=True):
                st.subheader("Visualization Output")

                if generate_chart_btn:
                    filtered_df = df.copy()

                    if numeric_filter_col != "None" and value_range is not None:
                        filtered_df = filtered_df[
                            (filtered_df[numeric_filter_col] >= value_range[0])
                            & (filtered_df[numeric_filter_col] <= value_range[1])
                        ]
                    if cat_filter_col != "None" and selected_categories:
                        filtered_df = filtered_df[
                            filtered_df[cat_filter_col].isin(selected_categories)
                        ]

                    if filtered_df.empty:
                        st.warning("No data matches the current filters — try widening them.")
                    else:
                        fig = None
                        try:
                            if chart_type == "Histogram":
                                fig = px.histogram(
                                    filtered_df, x=x_axis,
                                    color=None if group_col == "None" else group_col,
                                    marginal="box", title=f"Histogram of {x_axis}",
                                )
                            elif chart_type == "Box Plot":
                                fig = px.box(
                                    filtered_df,
                                    x=None if group_col == "None" else group_col,
                                    y=x_axis,
                                    color=None if group_col == "None" else group_col,
                                    title="Box Plot",
                                )
                            elif chart_type == "Scatter Plot":
                                if not y_axis or y_axis == "None":
                                    st.warning("Scatter plot requires a Y axis")
                                else:
                                    fig = px.scatter(
                                        filtered_df, x=x_axis, y=y_axis,
                                        color=None if group_col == "None" else group_col,
                                        title=f"Scatter: {x_axis} vs {y_axis}",
                                    )
                            elif chart_type == "Line Chart":
                                if not y_axis or y_axis == "None":
                                    st.warning("Line chart requires a Y axis")
                                else:
                                    fig = px.line(
                                        filtered_df, x=x_axis, y=y_axis,
                                        color=None if group_col == "None" else group_col,
                                        title=f"Line Chart: {x_axis} vs {y_axis}",
                                    )
                            elif chart_type == "Grouped Bar Chart":
                                if not y_axis or y_axis == "None":
                                    st.warning("Bar chart requires a Y axis")
                                else:
                                    temp_df = filtered_df.copy()
                                    y_col   = y_axis
                                    if aggregation != "None":
                                        grouped = temp_df.groupby(x_axis)[y_col]
                                        if aggregation == "Sum":
                                            temp_df = grouped.sum().reset_index()
                                        elif aggregation == "Mean":
                                            temp_df = grouped.mean().reset_index()
                                        elif aggregation == "Median":
                                            temp_df = grouped.median().reset_index()
                                        elif aggregation == "Count":
                                            cnt_col = f"{y_col}_count"
                                            temp_df = (temp_df.groupby(x_axis)[y_col]
                                                       .count().reset_index(name=cnt_col))
                                            y_col   = cnt_col
                                    fig = px.bar(
                                        temp_df, x=x_axis, y=y_col,
                                        color=None if group_col == "None" else group_col,
                                        barmode="group", title="Grouped Bar Chart",
                                    )
                            elif chart_type == "Correlation Heatmap":
                                if not numeric_cols:
                                    st.warning("No numeric columns for correlation heatmap")
                                else:
                                    corr = filtered_df[numeric_cols].corr()
                                    fig  = px.imshow(
                                        corr, text_auto=True,
                                        color_continuous_scale="RdBu_r",
                                        title="Correlation Heatmap",
                                    )

                            if fig is not None:
                                st.plotly_chart(fig, width="stretch")

                        except Exception as e:
                            st.error(f"Chart generation error: {e}")


with exportReportTab:
    show_toast()

    st.header("Export & Report")
    st.write("Export your cleaned dataset, transformation logs and reproducible workflow")

    df          = st.session_state.df
    df_original = st.session_state.history[0] if st.session_state.history else df

    st.subheader("Final Metrics")
    c1, c2, c3, c4, c5 = st.columns(5)

    final_rows = df.shape[0]        if df          is not None else 0
    final_cols = df.shape[1]        if df          is not None else 0
    orig_rows  = df_original.shape[0] if df_original is not None else 0
    orig_cols  = df_original.shape[1] if df_original is not None else 0

    with c1: st.metric("Final Rows",              f"{final_rows:,}", delta=final_rows - orig_rows)
    with c2: st.metric("Final Columns",           final_cols,        delta=final_cols - orig_cols)
    with c3: st.metric("Transformations Applied", st.session_state.transformation_count)
    with c4: st.metric("Validation Violations",   st.session_state.validation_violations)
    with c5:
        last_ts = st.session_state.logs[-1]["timestamp"] if st.session_state.logs else "—"
        st.metric("Last Change", last_ts)

    st.divider()
    st.subheader("Export Options")
    exportCol, reportCol = st.columns(2)

    with exportCol:
        with st.container(border=True):
            st.subheader("Export Dataset")
            st.write("Download dataset in your preferred format")
            if df is not None:
                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="cleaned_dataset.csv", mime="text/csv", width="stretch",
                )
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)
                st.download_button(
                    "Download Excel",
                    data=excel_buffer.getvalue(),
                    file_name="cleaned_dataset.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )
            else:
                st.info("No dataset loaded")

    with reportCol:
        with st.container(border=True):
            st.subheader("Transformation Report")
            st.write(
                "Download a detailed log of all operations applied, "
                "including parameters and timestamps"
            )
            if st.session_state.logs:
                st.download_button(
                    "Download report (.json)",
                    data=json.dumps(
                        st.session_state.logs, indent=2, default=str
                    ).encode("utf-8"),
                    file_name="transformation_report.json",
                    mime="application/json", width="stretch",
                )
            else:
                st.info("No transformations logged yet")

    st.divider()
    recipeCol, scriptCol = st.columns(2)

    with recipeCol:
        st.subheader("Export Workflow Recipe")
        st.write(
            "Download a machine-readable JSON file representing the transformation pipeline"
        )
        if st.session_state.logs:
            recipe = {
                "version":    "1.0",
                "created_at": datetime.now().isoformat(),
                "steps":      st.session_state.logs,
            }
            st.download_button(
                "Download Recipe (.json)",
                data=json.dumps(recipe, indent=2, default=str).encode("utf-8"),
                file_name="workflow_recipe.json", mime="application/json", width="stretch",
            )
        else:
            st.info("No transformations to export")

    with scriptCol:
        st.subheader("Replay Script")
        st.write(
            "Generate a pandas-based Python script that describes the transformation steps"
        )
        if st.session_state.logs:
            lines = [
                "import pandas as pd", "",
                "# Auto-generated replay script",
                "df = pd.read_csv('your_file.csv')  # or pd.read_excel(...)", "",
            ]
            for entry in st.session_state.logs:
                lines.append(
                    f"# Step {entry['step']}: {entry['action']} — {entry['timestamp']}"
                )
                lines.append(f"# Details: {json.dumps(entry['details'], default=str)}")
                lines.append("")
            script_text = "\n".join(lines)
            st.download_button(
                "Download .py file",
                data=script_text.encode("utf-8"),
                file_name="replay_script.py", mime="text/x-python", width="stretch",
            )
            with st.expander("Preview script"):
                st.code(script_text, language="python")
        else:
            st.info("No transformations to generate a script for")

    st.divider()

    with st.container(border=True):
        st.subheader("Transformation Log")
        st.write(f"Steps applied: **{st.session_state.transformation_count}**")
        if st.session_state.logs:
            st.dataframe(pd.DataFrame(st.session_state.logs), width="stretch")
        else:
            st.info("No transformations recorded yet")

        undoCol, resetCol = st.columns(2)
        with undoCol:
            if st.button("Undo Last Applied Step", key="export_undo"):
                undo()
                st.rerun()
        with resetCol:
            if st.button("Reset All Transformations", key="export_reset"):
                reset_all()
                st.rerun()

    with st.container(border=True):
        st.subheader("Recipe JSON Preview")
        if st.session_state.logs:
            st.json({
                "version":    "1.0",
                "created_at": datetime.now().isoformat(),
                "steps":      st.session_state.logs,
            })
        else:
            st.info("No transformations to preview")