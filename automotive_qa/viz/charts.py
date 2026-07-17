import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Premium Color Palette
THEME_COLORS = {
    'primary': '#0ea5e9',    # Sky Blue
    'secondary': '#0d9488',  # Teal
    'success': '#10b981',    # Emerald
    'danger': '#ef4444',     # Red
    'warning': '#f59e0b',    # Amber
    'neutral': '#64748b',    # Slate
    'background': '#ffffff', # White (Light theme)
    'paper': '#f8fafc',      # Slate 50
    'text': '#1e293b'        # Slate 800
}

def apply_premium_layout(fig, title_text):
    """Applies clean, modern styling to any Plotly figure."""
    # Determine if legend should be shown
    has_legend = False
    if fig.layout.showlegend is True:
        has_legend = True
    elif fig.layout.showlegend is None:
        # If not explicitly set, show legend if there is more than 1 trace or colors
        has_legend = len(fig.data) > 1

    fig.update_layout(
        title={
            'text': title_text,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 16, 'color': THEME_COLORS['text'], 'family': 'Outfit, Inter, sans-serif'}
        },
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font={'color': THEME_COLORS['text'], 'family': 'Inter, sans-serif'},
        hoverlabel=dict(
            bgcolor='#ffffff',
            font_size=12,
            font_family="Inter, sans-serif",
            font_color='#1e293b',
            bordercolor='#e2e8f0'
        ),
        margin=dict(l=50, r=150 if has_legend else 50, t=60, b=100),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=10),
            title=dict(text="")  # Clears redundant titles like 'variable'
        ),
        legend_title_text=""
    )
    
    # Update axes styling if they exist
    fig.update_xaxes(
        gridcolor='#e2e8f0', # Slate 200
        zerolinecolor='#cbd5e1',
        tickfont=dict(size=10),
        title_font=dict(size=11)
    )
    fig.update_yaxes(
        gridcolor='#e2e8f0',
        zerolinecolor='#cbd5e1',
        tickfont=dict(size=10),
        title_font=dict(size=11)
    )

def plot_horizontal_bar(df, x_col, y_col, title):
    """Renders a beautiful horizontal bar chart."""
    if df.empty:
        return go.Figure()
        
    df_sorted = df.sort_values(by=x_col, ascending=True)
    
    fig = px.bar(
        df_sorted, 
        x=x_col, 
        y=y_col, 
        orientation='h',
        color=x_col,
        color_continuous_scale=[[0, '#818cf8'], [1, '#4f46e5']], # Gradient effect
        text=x_col
    )
    fig.update_traces(
        textposition='outside',
        marker_line_color=THEME_COLORS['primary'],
        marker_line_width=1,
        opacity=0.9
    )
    fig.update_coloraxes(showscale=False)
    apply_premium_layout(fig, title)
    return fig

def plot_line_trend(df, x_col, y_cols, title):
    """Renders a chronologically ordered line chart with markers. Supports multiple y-columns."""
    if df.empty:
        return go.Figure()
        
    fig = px.line(
        df, 
        x=x_col, 
        y=y_cols, 
        markers=True,
        line_shape='linear',
        color_discrete_sequence=[THEME_COLORS['primary'], THEME_COLORS['secondary'], THEME_COLORS['success'], THEME_COLORS['warning'], THEME_COLORS['danger']]
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8, line=dict(color=THEME_COLORS['text'], width=1))
    )
    apply_premium_layout(fig, title)
    return fig

def plot_donut_chart(df, labels_col, values_col, title):
    """Renders a modern donut pie chart."""
    if df.empty:
        return go.Figure()
        
    fig = px.pie(
        df, 
        names=labels_col, 
        values=values_col, 
        hole=0.4,
        color_discrete_sequence=[THEME_COLORS['primary'], THEME_COLORS['secondary'], THEME_COLORS['success'], THEME_COLORS['warning'], THEME_COLORS['danger']]
    )
    fig.update_traces(
        textinfo='percent+label',
        marker=dict(line=dict(color=THEME_COLORS['background'], width=2))
    )
    apply_premium_layout(fig, title)
    return fig

def plot_histogram(df, value_col, title, bins=30):
    """Renders a mileage frequency distribution histogram."""
    if df.empty:
        return go.Figure()
        
    fig = px.histogram(
        df, 
        x=value_col,
        nbins=bins,
        color_discrete_sequence=[THEME_COLORS['secondary']]
    )
    fig.update_traces(
        opacity=0.85,
        marker_line_color=THEME_COLORS['background'],
        marker_line_width=0.5
    )
    apply_premium_layout(fig, title)
    fig.update_layout(bargap=0.05)
    return fig

def plot_radar_comparison(df, categories_col, metrics_cols, title):
    """Renders a spider/radar comparison chart across multiple models."""
    if df.empty:
        return go.Figure()
        
    fig = go.Figure()
    
    # Cap radar to top 9 models for readable output
    df_limited = df.head(9)
    
    # Normalize metrics to [0, 10] scale for visual alignment on the radar
    for col in metrics_cols:
        max_val = df_limited[col].max()
        val_series = df_limited[col]
        if max_val > 0:
            norm_vals = (val_series / max_val) * 10
        else:
            norm_vals = val_series
            
        fig.add_trace(go.Scatterpolar(
            r=norm_vals,
            theta=df_limited[categories_col],
            fill='toself',
            name=col
        ))
        
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                gridcolor='#334155',
                linecolor='#334155'
            ),
            angularaxis=dict(
                gridcolor='#334155',
                linecolor='#334155'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True
    )
    apply_premium_layout(fig, title)
    return fig

def plot_grouped_bar(df, x_col, y_cols, title):
    """Renders a grouped bar chart for comparisons."""
    if df.empty:
        return go.Figure()
        
    # Cap to top 15 rows for readable layout
    df_limited = df.head(15)
        
    fig = px.bar(
        df_limited, 
        x=x_col, 
        y=y_cols, 
        barmode='group',
        color_discrete_sequence=[THEME_COLORS['primary'], THEME_COLORS['secondary'], THEME_COLORS['success'], THEME_COLORS['warning'], THEME_COLORS['danger']]
    )
    apply_premium_layout(fig, title)
    return fig

def plot_scatter_plot(df, x_col, y_col, title):
    """Renders a scatter plot (Seaborn scatterplot equivalent)."""
    if df.empty:
        return go.Figure()
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color_discrete_sequence=[THEME_COLORS['primary']]
    )
    fig.update_traces(marker=dict(size=9, opacity=0.85, line=dict(width=1, color='#ffffff')))
    apply_premium_layout(fig, title)
    return fig

def plot_box_plot(df, x_col, y_col, title):
    """Renders a box plot showing data distribution (Seaborn boxplot equivalent)."""
    if df.empty:
        return go.Figure()
    fig = px.box(
        df,
        x=x_col,
        y=y_col,
        color_discrete_sequence=[THEME_COLORS['secondary']]
    )
    apply_premium_layout(fig, title)
    return fig

def plot_violin_plot(df, x_col, y_col, title):
    """Renders a violin plot (Seaborn violinplot equivalent)."""
    if df.empty:
        return go.Figure()
    fig = px.violin(
        df,
        x=x_col,
        y=y_col,
        box=True,
        points="all",
        color_discrete_sequence=[THEME_COLORS['success']]
    )
    apply_premium_layout(fig, title)
    return fig

def plot_area_chart(df, x_col, y_cols, title):
    """Renders a filled stacked area chart (Matplotlib stackplot equivalent)."""
    if df.empty:
        return go.Figure()
    fig = px.area(
        df,
        x=x_col,
        y=y_cols,
        color_discrete_sequence=[THEME_COLORS['primary'], THEME_COLORS['secondary'], THEME_COLORS['success']]
    )
    apply_premium_layout(fig, title)
    return fig


def build_plotly_figure(chart_type, df, title):
    """Renders the appropriate Plotly figure based on the selector type. Handles dataframe preprocessing."""
    if df.empty:
        return None
        
    # Copy dataframe to prevent mutating original data
    df = df.copy()
    
    # Drop duplicate rows
    df = df.drop_duplicates()
    
    # Drop rows that have proper NaN/None values
    df = df.dropna()
    
    import pandas.api.types as ptypes
    
    # Also drop rows where any column contains literal "nan", "none", "null", "0", 0, or empty strings
    for col in df.columns:
        if ptypes.is_numeric_dtype(df[col]):
            df = df[df[col] != 0]
        else:
            mask = df[col].astype(str).str.strip().str.lower().isin(['', 'nan', 'none', 'null', 'na', '0'])
            df = df[~mask]
            
    if df.empty:
        return None
    
    import pandas.api.types as ptypes
    
    # If the dataframe has only 1 column and it is non-numeric, convert it to a frequency count so we can plot it
    if len(df.columns) == 1 and not ptypes.is_numeric_dtype(df[df.columns[0]]):
        col_name = df.columns[0]
        df = df[col_name].value_counts().reset_index()
        df.columns = [col_name, "count"]
        
    # Ensure numeric columns are properly cast and clean up non-numeric columns for y-axes
    x_col = "period" if "period" in df.columns else df.columns[0]
    for c in df.columns:
        if c not in [x_col, "report_year", "report_month"]:
            try:
                df[c] = pd.to_numeric(df[c])
            except Exception:
                pass
                
    fig = None
    if chart_type == "horizontal_bar":
        # Ensure numeric value column
        val_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_horizontal_bar(df, val_col, df.columns[0], title)
    elif chart_type == "line":
        y_cols = [c for c in df.columns if c not in [x_col, "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        if not y_cols and len(df.columns) > 1:
            try:
                df[df.columns[1]] = pd.to_numeric(df[df.columns[1]], errors='coerce')
                y_cols = [df.columns[1]]
            except:
                pass
        fig = plot_line_trend(df, x_col, y_cols, title)
    elif chart_type == "donut":
        val_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_donut_chart(df, df.columns[0], val_col, title)
    elif chart_type == "histogram":
        val_col = df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_histogram(df, val_col, title)
    elif chart_type == "radar":
        y_cols = [c for c in df.columns if c not in [df.columns[0], "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_radar_comparison(df, df.columns[0], list(y_cols[:3]), title)
    elif chart_type == "grouped_bar":
        y_cols = [c for c in df.columns if c not in [df.columns[0], "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_grouped_bar(df, df.columns[0], list(y_cols), title)
    elif chart_type == "scatter":
        x_val = df.columns[0]
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[x_val] = pd.to_numeric(df[x_val], errors='coerce')
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_scatter_plot(df, x_val, y_val, title)
    elif chart_type == "box":
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_box_plot(df, df.columns[0], y_val, title)
    elif chart_type == "violin":
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_violin_plot(df, df.columns[0], y_val, title)
    elif chart_type == "area":
        y_cols = [c for c in df.columns if c not in [x_col, "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_area_chart(df, x_col, list(y_cols), title)
        
    return fig
