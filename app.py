##import section
import streamlit as st
import pandas as pd
import plotly.express as px

##setting the page up
st.set_page_config(layout="wide")

##data frame idk better to have it before the sidebar
df = None

##setting simple sidebar (will need change)
with st.sidebar:
    spaceLeft, mainContent, spaceRight = st.columns([0.5, 2, 0.5])

    with mainContent:
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            label="Upload file",
            type=["csv", "xlsx", "xlsm", "xlsb", "xltx", "xltm", "xls"]
        )
        ##we have different functions for csv and excel... sooo i just check the extension :)
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="ignore")

        st.write("Workflow")
        st.button("Reset Session")
        st.button("Undo Last Step")

        st.write("Logs")
        st.space(size=1)
        st.write("Here must be logs...")
        st.space(size=1)
        st.write("View full log")

##setting tabs to scroll through (will need change)
overviewTab, cleaningStudioTab, visualizationTab, exportReportTab =\
      st.tabs(["Overview", "Cleaning Studio", "Visualization", "Export & Report"],\
              width = 1490,\
              default = "Overview")

##setting overview tab (will need change)
with overviewTab:
    st.header("Dataset Overview")
    st.write("Here you can explore uploaded dataset metrics")
    
    ##added variables and list not to get error about undefined columns
    ##also made changes to the if statemnt, not to get errors here too
    ##because we had error when dataset was not uploaded 
    ##everything was placed under the logical and well defined condition
    datetime_columns = []
    numeric_columns = 0
    categorical_columns = 0

    ## i added rough calculation of metrics (will maybe need change too because of speed of loading)
    if df is not None:
        rows = df.shape[0]
        columns = df.shape[1]
        column_names = df.columns.tolist()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        # Loop through all columns to detect datetime columns
        #broad datetime handling to find datetimes inside of the excel and csv files

        datetime_columns = []
        for col in df.columns:
                    if df[col].dtype == "object":
                        converted = pd.to_datetime(df[col], errors="coerce")
                        if converted.notna().sum() / len(df[col]) > 0.8:
                            datetime_columns.append(col)
        datetime_column_count = len(datetime_columns)
        categorical_cols = [col for col in categorical_cols if col not in datetime_columns]
        numeric_columns = len(numeric_cols)
        categorical_columns = len(categorical_cols)

    else:
        rows = columns = 0
        column_names = []
        numeric_cols = []
        categorical_cols = []
        datetime_cols = []
        datetime_columns = []
        numeric_columns = categorical_columns = datetime_column_count = 0

    ##need for safe joins of lists, and just not to see any errors
    ##we made a mistake
    def safe_join(cols):
        return ", ".join(cols) if cols else "None"

    ##setting columns inside of the overview tab
    rowsColumn, columnsColumn, numericColumn, categoricalColumn, datetimeColumn = st.columns([2, 2, 2, 2, 2])

    ##i added names of columns, cat-num-date columns to debug them
    with rowsColumn:
        st.header(rows)
        st.write("Rows")

    with columnsColumn:
        st.header(columns)
        st.write("Columns")
        st.write(safe_join(column_names))

    with numericColumn:
        st.header(numeric_columns)
        st.write("Numeric Columns")
        st.write(safe_join(numeric_cols))

    with categoricalColumn:
        st.header(categorical_columns)
        st.write("Categorical Columns")
        st.write(safe_join(categorical_cols))

    with datetimeColumn:
        st.header(datetime_column_count)
        st.write("Datetime Columns")
        st.write(safe_join(datetime_columns))

    st.space(size=20)

    st.header(f"Total columns: {columns}")

    st.space(size=20)

    st.header("Data Profiling")

    st.space(size=20)

    ##setting separate column field to create layout inside of overview section
    datatypesColumn, mvDPColumn = st.columns([4, 4])

    ##trying to get all types of columns, names, etc, we will think about changing it a bit and finishing that, some fields
    ##are now duplicated but we will fix it (will need change)
    with datatypesColumn:
        st.header("Data Types")

        if df is not None:
            ##changed variables to show it correct
            st.write(f"Numeric columns: {numeric_columns}")
            st.write(f"Categorical columns: {categorical_columns}")
            st.write(f"Datetime columns: {datetime_column_count}")

            st.space(size=10)

            st.subheader("Column Names")

            st.write("Numeric:", safe_join(numeric_cols))
            st.write("Categorical:", safe_join(categorical_cols))
            st.write("Datetime:", safe_join(datetime_columns))

        else:
            st.write("No dataset loaded")


    ##checking for missing values
    with mvDPColumn:
        st.header("Missing Values")

        if df is not None:
            missing_per_column = df.isnull().sum()
            total_missing = int(missing_per_column.sum())

            st.write(f"Total missing values: {total_missing}")

            missing_columns = missing_per_column[missing_per_column > 0]

            if missing_columns.empty:
                st.write("No missing values found")
            else:
                for col, count in missing_columns.items():
                    st.write(f"{col}: {count}")
        else:
            st.write("No dataset loaded")

        st.space(size=50)

    ##checking for duplicates
    with mvDPColumn:
        st.header("Duplicates")

        if df is not None:
            duplicate_count = df.duplicated().sum()

            st.write(f"Total duplicate rows: {duplicate_count}")

            if duplicate_count > 0:
                if st.button("Remove Duplicates"):
                    df = df.drop_duplicates()
                    st.success("Duplicate rows removed")
        else:
            st.write("No dataset loaded")

    st.space(size=10)

    ##setting separate column field to create layout inside of overview section
    datatypesColumn, mvDPColumn = st.columns([4, 4])

##Cleaning studio tab
with cleaningStudioTab:
    st.header("Cleaning Studio")
    st.write("Clean, transform, and prepare your dataset with different options")

    if df is None:
        st.info("Upload dataset first")
        st.stop()

    mainColumn, metricsColumn = st. columns([4, 4])

    ##main columns setup (will need change)
    with mainColumn:
        ##added cleaning and calculating affected rows with missing values and duplicates
        ##now we are good to go and finish cleaning studio
        ##we are left with 6 easier parts
        ##then we will think about states, caching and other stuff
        with st.expander("Missing values"):

            selected_cols = st.multiselect(
                "Columns",
                df.columns.tolist(),
            )

            if not selected_cols:
                st.warning("Select at least one column")
            else:
                missing_counts = df[selected_cols].isna().sum()
                st.write(missing_counts[missing_counts > 0])

                action = st.selectbox(
                    "Action",
                    [
                        "Drop rows",
                        "Fill numeric with median",
                        "Fill numeric with mean",
                        "Fill categorical with mode",
                        "Fill with custom value",
                    ],
                )

                custom_value = None
                if action == "Fill with custom value":
                    custom_value = st.text_input("Custom value")

                if st.button("Apply", key="mv_apply"):

                    new_df = df.copy()

                    if action == "Drop rows":
                        before = len(new_df)
                        new_df = new_df.dropna(subset=selected_cols)
                        rows_affected = before - len(new_df)

                    else:
                        rows_affected = 0

                        for col in selected_cols:
                            mask = new_df[col].isna()
                            count = mask.sum()

                            if count == 0:
                                continue

                            if action == "Fill numeric with median" and pd.api.types.is_numeric_dtype(new_df[col]):
                                new_df.loc[mask, col] = new_df[col].median()

                            elif action == "Fill numeric with mean" and pd.api.types.is_numeric_dtype(new_df[col]):
                                new_df.loc[mask, col] = new_df[col].mean()

                            elif action == "Fill categorical with mode" and not pd.api.types.is_numeric_dtype(new_df[col]):
                                mode = new_df[col].mode(dropna=True)
                                if not mode.empty:
                                    new_df.loc[mask, col] = mode.iloc[0]

                            elif action == "Fill with custom value":
                                new_df.loc[mask, col] = custom_value

                            rows_affected += count

                    st.success(f"Rows affected: {rows_affected}")

        ##added duplicate handling part, almost the same base functionality as missing values
        ##now we can remove duplicates from the dataset
        with st.expander("Duplicate handling"):

            mode = st.radio(
                "Check duplicates by",
                ["All columns", "Selected columns"]
            )

            subset_cols = None
            if mode == "Selected columns":
                subset_cols = st.multiselect("Columns", df.columns.tolist())

                if not subset_cols:
                    st.warning("Select at least one column")
                    st.stop()

            keep_option = st.selectbox(
                "Action",
                ["Keep first", "Keep last", "Remove all duplicates"]
            )

            if keep_option == "Keep first":
                dup_mask = df.duplicated(subset=subset_cols, keep="first")
            elif keep_option == "Keep last":
                dup_mask = df.duplicated(subset=subset_cols, keep="last")
            else:
                dup_mask = df.duplicated(subset=subset_cols, keep=False)

            dup_count = dup_mask.sum()
            st.write(f"Duplicate rows: {dup_count}")

            if dup_count > 0:
                st.dataframe(df[dup_mask].head(20))

            if st.button("Apply", key="dup_apply"):

                if keep_option == "Keep first":
                    new_df = df.drop_duplicates(subset=subset_cols, keep="first")

                elif keep_option == "Keep last":
                    new_df = df.drop_duplicates(subset=subset_cols, keep="last")

                else:
                    new_df = df[~df.duplicated(subset=subset_cols, keep=False)]

                rows_removed = len(df) - len(new_df)

                st.success(f"Removed {rows_removed} duplicate rows")

        with st.expander("Data type conversion"):
            st.header("Data type conversion")

            selected_cols = st.multiselect(
                "Select columns",
                df.columns.tolist()
            )

            if not selected_cols:
                st.warning("Select at least one column")
            else:
                conversion_type = st.selectbox(
                    "Conversion type",
                    [
                        "To numeric",
                        "To categorical",
                        "To datetime"
                    ]
                )

                datetime_format = None
                clean_numeric = False

                if conversion_type == "To datetime":
                    datetime_format = st.text_input(
                        "Datetime format (optional, e.g. %Y-%m-%d)"
                    )

                if conversion_type == "To numeric":
                    clean_numeric = st.checkbox(
                        "Clean numeric strings (remove commas, currency symbols)"
                    )

                def clean_numeric_series(series: pd.Series) -> pd.Series:
                    return (
                        series.astype(str)
                        .str.replace(r"[,\$\€\£]", "", regex=True)
                        .str.replace(r"\s+", "", regex=True)
                    )

                def convert_numeric(series: pd.Series) -> pd.Series:
                    if clean_numeric:
                        series = clean_numeric_series(series)
                    return pd.to_numeric(series, errors="coerce")

                def convert_datetime(series: pd.Series) -> pd.Series:
                    return pd.to_datetime(
                        series,
                        format=datetime_format if datetime_format else None,
                        errors="coerce"
                    )

                def convert_categorical(series: pd.Series) -> pd.Series:
                    return series.astype("category")

                conversion_map = {
                    "To numeric": convert_numeric,
                    "To datetime": convert_datetime,
                    "To categorical": convert_categorical,
                }

                if st.button("Apply", key="dtype_apply"):

                    new_df = df.copy()

                    total_rows_affected = 0
                    total_errors = 0
                    processed_columns = 0

                    for col in selected_cols:
                        series = new_df[col]

                        try:
                            before_na = series.isna().sum()
                            before_non_na = series.notna().sum()

                            convert_fn = conversion_map[conversion_type]
                            converted = convert_fn(series)

                            after_na = converted.isna().sum()


                            conversion_errors = max(after_na - before_na, 0)

                            changes_mask = ~(series == converted) & ~(series.isna() & converted.isna())
                            rows_changed = changes_mask.sum()

                            new_df[col] = converted

                            total_rows_affected += rows_changed
                            total_errors += conversion_errors
                            processed_columns += 1

                        except Exception as e:
                            total_errors += 1
                            st.warning(f"Error processing column '{col}': {e}")

                    st.success(f"Columns processed: {processed_columns}")
                    st.info(f"Rows actually changed: {total_rows_affected}")
                    st.warning(f"Values coerced to NaN (conversion errors): {total_errors}")

        with st.expander("Categorical cleaning"):
            st.header("Categorical cleaning")

            selected_cols = st.multiselect(
                "Select categorical columns",
                df.columns.tolist()
            )

            if not selected_cols:
                st.warning("Select at least one column")
            else:

                st.subheader("Basic cleaning")

                trim_whitespace = st.checkbox("Trim whitespace")
                to_lower = st.checkbox("Convert to lowercase")
                to_title = st.checkbox("Convert to title case")

                invalid_case = to_lower and to_title
                if invalid_case:
                    st.error("Choose either lowercase OR title case")

                st.subheader("Value mapping")

                enable_mapping = st.checkbox("Enable mapping")

                mapping_df = None
                set_unmatched_other = False
                other_value = "Other"

                if enable_mapping:
                    unique_values = pd.Series(dtype="object")

                    for col in selected_cols:
                        unique_values = pd.concat([
                            unique_values,
                            df[col].dropna().astype(str)
                        ])

                    unique_values = pd.Series(unique_values.unique()).sort_values()

                    mapping_df = pd.DataFrame({
                        "old_value": unique_values,
                        "new_value": unique_values
                    })

                    mapping_df = st.data_editor(mapping_df, num_rows="dynamic")

                    if mapping_df["old_value"].duplicated().any():
                        st.error("Duplicate 'old_value' detected in mapping")
                        st.stop()

                    if mapping_df["new_value"].isna().any():
                        st.warning("Some new values are empty")

                    set_unmatched_other = st.checkbox("Set unmatched values to 'Other'")
                    if set_unmatched_other:
                        other_value = st.text_input("Other value", value="Other")

            st.subheader("Rare category grouping")

            enable_rare = st.checkbox("Enable rare category grouping")

            rare_threshold = 0.05
            rare_label = "Other"

            if enable_rare:
                rare_threshold = st.slider(
                    "Threshold (%)",
                    0.0, 1.0, 0.05, 0.01
                )
                rare_label = st.text_input("Rare category label", value="Other")

            st.subheader("Encoding")
            one_hot = st.checkbox("Apply one-hot encoding")

            if st.button("Apply", key="cat_clean_apply"):

                if invalid_case:
                    st.warning("Fix errors before applying")
                else:

                    new_df = df.copy()

                    total_rows_affected = 0
                    total_columns_affected = 0

                    mapping_dict = None
                    if enable_mapping and mapping_df is not None:
                        mapping_dict = dict(
                            zip(mapping_df["old_value"], mapping_df["new_value"])
                        )

                    for col in selected_cols:
                        try:
                            series = new_df[col]
                            original = series.copy()

                            mask = series.notna()
                            working = series[mask].astype(str)

                            if trim_whitespace:
                                working = working.str.strip()

                            if to_lower:
                                working = working.str.lower()

                            if to_title:
                                working = working.str.title()

                            if mapping_dict is not None:
                                mapped = working.map(mapping_dict)

                                if set_unmatched_other:
                                    working = mapped.fillna(other_value)
                                else:
                                    working = mapped.where(mapped.notna(), working)

                            if enable_rare:
                                freq = working.value_counts(normalize=True)
                                rare_values = freq[freq < rare_threshold].index

                                if len(rare_values) > 0:
                                    working = working.where(
                                        ~working.isin(rare_values),
                                        rare_label
                                    )

                            series.loc[mask] = working
                            new_df[col] = series

                            changes = ~(original.eq(new_df[col]) | (original.isna() & new_df[col].isna()))
                            rows_changed = changes.sum()

                            if rows_changed > 0:
                                total_rows_affected += rows_changed
                                total_columns_affected += 1

                        except Exception as e:
                            st.warning(f"Error processing column '{col}': {e}")

                if one_hot:
                    try:
                        new_df = pd.get_dummies(new_df, columns=selected_cols)
                        total_columns_affected += len(selected_cols)
                    except Exception as e:
                        st.warning(f"One-hot encoding failed: {e}")

                st.success(f"Columns affected: {total_columns_affected}")
                st.info(f"Rows affected: {total_rows_affected}")

        with st.expander("Outlier handling"):
            st.header("Outlier handling")

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if not numeric_cols:
                st.warning("No numeric columns available")
                st.stop()

            selected_cols = st.multiselect(
                "Select numeric columns",
                numeric_cols,
                key="outlier_cols"
            )

            if not selected_cols:
                st.warning("Select at least one column")
            else:

                action = st.selectbox(
                    "Action",
                    ["Show only", "Cap (Winsorize)", "Remove rows"],
                    key="outlier_action"
                )

                lower_q = st.slider("Lower quantile", 0.0, 0.5, 0.05, 0.01, key="outlier_lq")
                upper_q = st.slider("Upper quantile", 0.5, 1.0, 0.95, 0.01, key="outlier_uq")

                def get_iqr_bounds(series: pd.Series):
                    q1 = series.quantile(0.25)
                    q3 = series.quantile(0.75)
                    iqr = q3 - q1
                    return q1 - 1.5 * iqr, q3 + 1.5 * iqr

                def detect_outliers(series: pd.Series):
                    lower, upper = get_iqr_bounds(series)
                    return (series < lower) | (series > upper)

                if st.button("Apply", key="outlier_apply"):

                    new_df = df.copy()

                    summary = []
                    total_outliers = 0
                    total_removed = 0
                    total_capped = 0

                    for col in selected_cols:
                        try:
                            series = new_df[col]

                            if series.isna().all():
                                st.warning(f"{col}: all values are NaN, skipped")
                                continue

                            mask = detect_outliers(series)
                            count = int(mask.sum())

                            total_outliers += count

                            col_info = {
                                "column": col,
                                "outliers": count,
                                "min": float(series.min()),
                                "max": float(series.max())
                            }

                            if action == "Cap (Winsorize)":
                                lower_cap = series.quantile(lower_q)
                                upper_cap = series.quantile(upper_q)

                                capped = series.clip(lower=lower_cap, upper=upper_cap)
                                changed = int((series != capped).sum())

                                total_capped += changed
                                new_df[col] = capped

                                col_info["capped"] = changed

                            summary.append(col_info)

                        except Exception as e:
                            st.warning(f"{col}: {e}")

                    if action == "Remove rows":
                        combined_mask = pd.Series(False, index=new_df.index)

                        for col in selected_cols:
                            combined_mask |= detect_outliers(new_df[col])

                        before = len(new_df)
                        new_df = new_df[~combined_mask]
                        total_removed = before - len(new_df)

                    st.success(f"Total outliers detected: {total_outliers}")

                    if action == "Cap (Winsorize)":
                        st.info(f"Values capped: {total_capped}")

                    if action == "Remove rows":
                        st.warning(f"Rows removed: {total_removed}")

                    st.dataframe(pd.DataFrame(summary))

        with st.expander("Scaling"):
            st.header("Scaling")

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if not numeric_cols:
                st.warning("No numeric columns available")
                st.stop()

            selected_cols = st.multiselect(
                "Select numeric columns",
                numeric_cols,
                key="scaling_cols"
            )

            if not selected_cols:
                st.warning("Select at least one column")
            else:

                method = st.selectbox(
                    "Scaling method",
                    ["Min-Max Scaling", "Z-score Standardization"],
                    key="scaling_method"
                )

                def min_max_scale(series: pd.Series):
                    min_val, max_val = series.min(), series.max()
                    if min_val == max_val:
                        return None
                    return (series - min_val) / (max_val - min_val)

                def z_score_scale(series: pd.Series):
                    mean, std = series.mean(), series.std()
                    if std == 0:
                        return None
                    return (series - mean) / std

                if st.button("Apply", key="scaling_apply"):

                    new_df = df.copy()
                    stats_output = []

                    for col in selected_cols:
                        try:
                            series = new_df[col]

                            if series.isna().all():
                                st.warning(f"{col}: all values are NaN, skipped")
                                continue

                            before = {
                                "mean": float(series.mean()),
                                "std": float(series.std()),
                                "min": float(series.min()),
                                "max": float(series.max())
                            }

                            if method == "Min-Max Scaling":
                                scaled = min_max_scale(series)
                            else:
                                scaled = z_score_scale(series)

                            if scaled is None:
                                st.warning(f"{col}: cannot scale (constant or zero std)")
                                continue

                            new_df[col] = scaled

                            after = {
                                "mean": float(scaled.mean()),
                                "std": float(scaled.std()),
                                "min": float(scaled.min()),
                                "max": float(scaled.max())
                            }

                            stats_output.append({
                                "column": col,
                                "before_mean": before["mean"],
                                "after_mean": after["mean"],
                                "before_std": before["std"],
                                "after_std": after["std"],
                                "before_min": before["min"],
                                "after_min": after["min"],
                                "before_max": before["max"],
                                "after_max": after["max"],
                            })

                        except Exception as e:
                            st.warning(f"{col}: {e}")

                    if stats_output:
                        st.dataframe(pd.DataFrame(stats_output))

                    st.success("Scaling applied successfully")

        with st.expander("Column operations"):
            st.header("Column operations")

        with st.expander("Data validation"):
            st.header("Data validation")

    with metricsColumn:
        st.header("Transformation preview")
        st.write("Rows")
        st.write("Columns")
        st.write("Rows affected")
        st.write("Columns affected")

    with metricsColumn:
        st.header("Transformation preview")
        st.write("Information loading...")
        st.write("Information loading...")
        st.write("Information loading...")
        st.write("Information loading...")

        ##setting up button columns (will need change)
        buttonUndoCleaningColumn, buttonResetCleaningColumn = st.columns([2, 2])
        with buttonUndoCleaningColumn:
            st.button("Undo Last Step")

        with buttonResetCleaningColumn:
            st.button("Reset All")

##Visalization TAb
with visualizationTab:
    st.header("Visualization")
    st.write("Create interactive charts and explore your dataset visually")

    if df is None:
        st.warning("Upload dataset first")
    else:
        numeric_cols = df.select_dtypes(include = "number").columns.tolist()
        categorical_cols = df.select_dtypes(include = ["object", "category"]).columns.tolist()
        ##checking only for columns where values inside are repeated not to get unique values in categories
        ##so we just multiply the number of rows of dataframe by 50% size of it and checking to have unique values
        categorical_cols = [
            col for col in categorical_cols
            if df[col].nunique() < len(df) * 0.5
        ]
        all_cols = df.columns.tolist()
        chartConfigColumn, chartOutputColumn = st.columns([1,1])

        ##fixed chart config part, we need better design for our work
        ##added value handling to use them in charts, cuz i cant draw graphs without that
        with chartConfigColumn:
            containerVisualizationTab = st.container(border=True)
            with containerVisualizationTab:
                st.header("Chart Configuration")

                st.space(size=20)

                st.header("Chart Type")
                chart_type = st.selectbox(
                        "",
                        [
                            "Histogram",
                            "Box Plot",
                            "Scatter Plot",
                            "Line Chart",
                            "Grouped Bar Chart",
                            "Correlation Heatmap",
                        ],
                    )

                st.space(size=20)

                st.header("Axes")

                x_axis = st.selectbox(
                    "X Axis",
                    all_cols
                )
                ##a little check just not to wait for values for Y-axis if they are none
                if numeric_cols:
                    y_axis = st.selectbox(
                        "Y Axis",
                        ["None"] + numeric_cols
                    )
                else:
                    st.warning("no numeric columns for y_axis")
                    y_axis = None

                st.space(size=20)

                st.header("Color/Group (Optional)")
                group_col = st.selectbox(
                        "Group by",
                        ["None"] + categorical_cols
                    )

                st.space(size=20)

                st.header("Aggregation")
                aggregation = st.selectbox(
                        "Aggregation method",
                        ["None", "Sum", "Mean", "Count", "Median"],
                    )

                st.space(size=20)

                st.header("Numeric Filter")
                numeric_filter_col = st.selectbox(
                        "Column",
                        ["None"] + numeric_cols
                    )

                value_range = None

                ##checking whole values because we will work mainly with index columns
                if numeric_filter_col != "None":
                    min_val = int(df[numeric_filter_col].min())
                    max_val = int(df[numeric_filter_col].max())
                    value_range = st.slider(
                        "Value Range",
                        min_val,
                        max_val,
                        (min_val, max_val),
                        step=1
                    )

                st.space(size=20)

                st.header("Categorical Filter")
                cat_filter_col = st.selectbox(
                        "Column",
                        ["None"] + categorical_cols
                    )
                selected_categories = []

                ##dropping all useless valeus and also getting selected categories
                if cat_filter_col != "None":
                    unique_vals = df[cat_filter_col].dropna().unique().tolist()
                    selected_categories = st.multiselect(
                        "Selected categories",
                        unique_vals
                    )

                st.space(size=20)

                genChart, resetFilt = st.columns([2,2])

                with genChart:
                    generate_chart_btn = st.button("Generate Chart")

                with resetFilt:
                    reset_filters_btn = st.button("Reset Filters")

        with chartOutputColumn:
            containerOutputVTab = st.container(border=True)
            with containerOutputVTab:
                st.header("Visualization Output")

                st.space(size=30)

                ##copying dataframe to work with it in charts
                if generate_chart_btn:
                    filtered_df = df.copy()
                    if numeric_filter_col != "None":
                        filtered_df = filtered_df[
                            (filtered_df[numeric_filter_col] >= value_range[0]) &
                            (filtered_df[numeric_filter_col] <= value_range[1])
                        ]

                    if cat_filter_col != "None" and selected_categories:
                        filtered_df = filtered_df[
                            filtered_df[cat_filter_col].isin(selected_categories)
                        ]

                    x_values = filtered_df.index if x_axis == "Index" else filtered_df[x_axis]
                    fig = None

                    if chart_type == "Histogram":
                        fig = px.histogram(filtered_df, x = x_values, color = None
                                           if group_col == "None"
                                           else group_col,
                                           marginal = "box", title = f"Histogram of {x_axis}")

                    elif chart_type == "Box Plot":
                        fig = px.box(filtered_df, x = None if group_col == "None" else group_col,
                                     y = x_axis, color = None if group_col == "None" else group_col, title = "Box Plot")

                    ##visualization works not well with y axis and 1 million records
                    ##soon will be optimized and fixed
                    elif chart_type == "Scatter Plot":
                        if y_axis == "None":
                            st.warning("scatter plot requires Y axis")
                        else:
                            fig = px.scatter(filtered_df, x = x_axis, y = y_axis, color = None if group_col == "None" else group_col)

                    elif chart_type == "Line Chart":
                        if y_axis == "None":
                            st.warning("line chart requires Y axis")
                        else:
                            fig = px.line(filtered_df, x = x_axis, y = y_axis, color = None if group_col == "None" else group_col,
                                          title = f"line chart: {x_axis} vs {y_axis}")

                    elif chart_type == "Grouped Bar Chart":

                        if y_axis=="None":
                            st.warning("Bar chart requires Y Axis")

                        else:
                            temp_df = filtered_df.copy()

                            if aggregation != "None":
                                grouped = temp_df.groupby(x_axis)[y_axis]

                                if aggregation == "Sum":
                                    temp_df = grouped.sum().reset_index()
                                elif aggregation == "Mean":
                                    temp_df = grouped.mean().reset_index()
                                elif aggregation == "Median":
                                    temp_df = grouped.median().reset_index()
                                elif aggregation == "Count":
                                    temp_df = temp_df.groupby(x_values)[y_axis].count().reset_index(name=f"{y_axis}_count")
                                    y_axis = f"{y_axis}_count"

                            fig = px.bar(
                                temp_df,
                                x=x_axis,
                                y=f"{y_axis}_count" if aggregation=="Count" else y_axis,
                                color=None if group_col=="None" else group_col,
                                barmode="group",
                                title="Grouped Bar Chart"
                            )

                    elif chart_type == "Correlation Heatmap":
                        corr = filtered_df[numeric_cols].corr()
                        fig = px.imshow(corr, text_auto = True, color_continuous_scale = "RdBu_r", title = "Correlation Heatmap")

                    if fig:
                        st.plotly_chart(fig, use_container_width = True)
#Export Tab
with exportReportTab:
    st.header("Export & Report")
    st.write("Export your cleared dataset, transformation logs and reproducible workflow")

    st.space(size=35)

    st.header("Final metrics")
    finalrowsColumn, finalcolumnsColumn, transformationsColumn, validationViolationsColumn, lastChangeColumn = st.columns([2, 2, 2, 2, 2])

    with finalrowsColumn:
        st.header("Number of")
        st.write("Final Rows")

    with finalcolumnsColumn:
        st.header("Number of")
        st.write("Final Columns")

    with transformationsColumn:
        st.header("Number of")
        st.write("Transformations Applied")

    with validationViolationsColumn:
        st.header("Number of")
        st.write("Validations Violated")

    with lastChangeColumn:
        st.header("Date")
        st.write("Last Change Date")

    st.header("Export Options")

    exportColumn, transformationReportColumn = st.columns([2,2])

    with exportColumn:
        exportContainer = st.container(border=True)
        with exportContainer:
            st.header("Export Dataset")
            st.write("Download dataset in your preferred format")

            dCSVColumn, dExcelColumn = st.columns([2,2])
            with dCSVColumn:
                st.button("Download CSV")

            with dExcelColumn:
                st.button("Download Excel")

    with transformationReportColumn:
        transformationReportContainer = st.container(border=True)
        with transformationReportContainer:
            st.header("Transformation Report")
            st.write("Download a detailed log of all operations applied, including parameters and timestamps")
            st.button("Download report (.json)")

    exportWorkflowRecipeColumn, replayScriptColumn = st.columns([2,2])

    with exportWorkflowRecipeColumn:
        st.header("Export Workflow Recipe")
        st.write("Download a machine readable JSON file representing the transformation pipeline")
        st.button("Download Recipe (.json)")

    with replayScriptColumn:
        st.header("Replay Script")
        st.write("Generate a pandas based Python script that reproduces the transformation steps")

        genScriptColumn, downloadPYColumn = st.columns([2,2])
        with genScriptColumn:
            st.button("Generate script")

        with downloadPYColumn:
            st.button("Download .py file")

    transformationContainer = st.container(border=True)
    with transformationContainer:
        st.header("Transformation Log")
        st.write("Number of steps applied")

        st.space(size=30)

        st.header("HERE WILL BE LOADED LOGS")

        undoLastStepColumn, resetAllTransformationsColumn = st.columns([2,2])
        with undoLastStepColumn:
            st.button("Undo Last Applied Step")

        with resetAllTransformationsColumn:
            st.button("Reset All Transformations")

    recipeJSONPreviewContainer = st.container(border=True)
    with recipeJSONPreviewContainer:
        st.header("Recipe JSON Preview")