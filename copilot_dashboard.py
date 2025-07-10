import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
sns.set(style="whitegrid")

st.title("🤖 Copilot Usage Dashboard")

uploaded_file = st.file_uploader("📁 Upload your Excel file", type=["xlsx", "xls"])
def aggregate_ai_used(series):
    if 'Yes' in series.values:
        return 'Yes'
    else:
        return 'No'
def get_average_rating(series):
    rating_map = {
        'Poor': 1,
        'Average': 2,
        'Good': 3,
        'Very Good': 4
    }
    scores = series.map(rating_map).dropna()
    if scores.empty:
        return 'Poor'
    avg_score = scores.mean()
    if avg_score < 1.5:
        return 'Poor'
    elif avg_score < 2.5:
        return 'Average'
    elif avg_score < 3.5:
        return 'Good'
    else:
        return 'Very Good'


aggregation_rules = {
    'Copilot Implemented': aggregate_ai_used,
    'Number of lines of code generated': 'sum',
    'Lines of Code Used': 'sum',
    'Sprint': 'first',
    'Overall Result (Good, Very Good, Average, Poor)':get_average_rating,
    'Developer Name':'first'
}
numeric_cols = [
    'Number of lines of code generated', 
    'Lines of Code Used', 
]
def calculate_usable_percentage(used_lines, generated_lines):
    if pd.isna(generated_lines) or generated_lines == 0:
        return 0.0
    if pd.isna(used_lines):
        return 0.0
    return (used_lines / generated_lines) * 100



def render_chart(fig, caption, chart_id):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    st.image(buf, caption=caption, use_container_width=True)
    st.download_button(
        label="📋 Copy/Download Image",
        data=buf.getvalue(),
        file_name=f"{chart_id}.png",
        mime="image/png",
        key=f"download_button_{chart_id}"
    )

if uploaded_file:
    original_df = pd.read_excel(uploaded_file)
    original_df['Story Number'] = original_df['Story Number'].astype(str).str.strip()
    for col in numeric_cols:
        original_df[col] = pd.to_numeric(original_df[col], errors='coerce')
        original_df[col] = original_df[col].fillna(0)

    df = original_df.groupby('Story Number').agg(aggregation_rules).reset_index()
    df['Usable Code %'] = df.apply(
        lambda row: calculate_usable_percentage(row['Lines of Code Used'], row['Number of lines of code generated']),
        axis=1
    )

    # Preprocessing
    df['Copilot Implemented'] = df['Copilot Implemented'].astype(str).str.strip().str.lower()
    df = df[df['Copilot Implemented'].notna() & (df['Copilot Implemented'] != '')]
    df['Number of lines of code generated'] = pd.to_numeric(df['Number of lines of code generated'], errors='coerce')
    df['Lines of Code Used'] = pd.to_numeric(df['Lines of Code Used'], errors='coerce')
    df['Usable Code %'] = pd.to_numeric(df['Usable Code %'], errors='coerce')
    df['Overall Result Clean'] = df['Overall Result (Good, Very Good, Average, Poor)'].astype(str).str.strip()

    st.success("✅ File loaded and cleaned successfully.")

    # Chart 1 - Overall: Total Tickets vs AI Use Applied
    total_tickets = len(df)
    ai_applied = len(df[df['Copilot Implemented'] == 'yes'])
    fig1, ax1 = plt.subplots()
    sns.barplot(x=['Total Tickets', 'AI Use Applied'], y=[total_tickets, ai_applied], ax=ax1)
    ax1.bar_label(ax1.containers[0])
    ax1.set_title("Overall: Total Tickets vs AI Use Applied")

    # Chart 2 - Sprint-wise: Total Tickets vs AI Use Applied
    sprint_group = df.groupby('Sprint').agg(
        Total_Tickets=('Story Number', 'count'),
        AI_Use_Applied=('Copilot Implemented', lambda x: (x == 'yes').sum())
    ).reset_index()
    melted = pd.melt(sprint_group, id_vars='Sprint', value_vars=['Total_Tickets', 'AI_Use_Applied'])
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    sns.barplot(data=melted, x='Sprint', y='value', hue='variable', ax=ax2)
    ax2.set_title("Sprint-wise: Total Tickets vs AI Use Applied")
    for container in ax2.containers:
        ax2.bar_label(container, padding=3)

    col1, col2 = st.columns(2)
    with col1:
        render_chart(fig1, "Chart 1: Overall Tickets vs AI Use", "chart1")
    with col2:
        render_chart(fig2, "Chart 2: Sprint-wise Tickets vs AI Use", "chart2")

    # Chart 3 - Overall Result Category for AI Applied
    ai_df = df[df['Copilot Implemented'] == 'yes']
    overall_counts = ai_df['Overall Result Clean'].value_counts()
    fig3, ax3 = plt.subplots()
    sns.barplot(x=overall_counts.index, y=overall_counts.values, ax=ax3)
    ax3.set_title("Overall: AI Use Applied vs Result Category")
    ax3.bar_label(ax3.containers[0])

    # Chart 4 - Sprint-wise Result Category
    color_map = {
    'Very Good': '#2ca02c',  # A nice green
    'Good': '#98df8a',       # A light green
    'Average': 'gold',       # Yellow
    'Poor': '#d62728' # A standard red
    }
    result_pivot = ai_df.groupby(['Sprint', 'Overall Result Clean']).size().unstack(fill_value=0).reset_index()
    melted_result = pd.melt(result_pivot, id_vars='Sprint', var_name='Result', value_name='Count')
    max_count = melted_result['Count'].max()
    min_height = max_count * 0.01 if max_count > 0 else 0.2
    
    # 2. Manipulate data for plotting by creating a new column
    melted_result['Count'] = melted_result['Count'].apply(
        lambda x: min_height if x == 0 else x
    )
    fig4, ax4 = plt.subplots(figsize=(12, 5))
    sns.barplot(data=melted_result, x='Sprint', y='Count', hue='Result', ax=ax4,palette=color_map)
    ax4.set_title("Sprint-wise: AI Use Applied vs Result Category")
    padding = 0.01 * ax4.get_ylim()[1]
    for container in ax4.containers:
        for bar in container.patches:
            height = bar.get_height()
            # If the plotted height is our tiny value, label as '0'
            label_text = '0' if height == min_height else f'{int(height)}'
            
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                height + padding,
                label_text,
                ha='center', va='bottom'
            )
    col3, col4 = st.columns(2)
    with col3:
        render_chart(fig3, "Chart 3: Overall Result Category", "chart3")
    with col4:
        render_chart(fig4, "Chart 4: Sprint-wise Result Category", "chart4")

    # Chart 5 - LOC Generated vs LOC Used
    loc_group = df.groupby('Sprint').agg(
        LOC_Generated=('Number of lines of code generated', 'sum'),
        LOC_Used=('Lines of Code Used', 'sum')
    ).reset_index()
    melted_loc = pd.melt(loc_group, id_vars='Sprint', value_vars=['LOC_Generated', 'LOC_Used'])
    fig5, ax5 = plt.subplots(figsize=(10, 4))
    sns.barplot(data=melted_loc, x='Sprint', y='value', hue='variable', ax=ax5)
    ax5.set_title("Sprint-wise: LOC Generated vs LOC Used")
    for container in ax5.containers:
        ax5.bar_label(container, fmt='%.0f', padding=2)

    # Chart 6 - Developer-wise Usable Code %
    ai_stories_df = df[df['Copilot Implemented'].str.lower() == 'yes']
    dev_code_use = ai_stories_df.groupby('Developer Name')['Usable Code %'].mean().sort_values(ascending=False)
    fig6, ax6 = plt.subplots(figsize=(10, 4))
    sns.barplot(x=dev_code_use.index, y=dev_code_use.values, ax=ax6)
    ax6.set_ylabel("Average Usable Code %")
    ax6.set_xlabel("Developer")
    ax6.set_xticklabels(dev_code_use.index, rotation=45, ha='right')
    ax6.set_title("Average Usable Code % by Developer")
    ax6.bar_label(ax6.containers[0], fmt='%.1f', padding=3)

    col5, col6 = st.columns(2)
    with col5:
        render_chart(fig5, "Chart 5: LOC Generated vs LOC Used", "chart5")
    with col6:
        render_chart(fig6, "Chart 6: Developer Usable Code %", "chart6")
        
    # Chart 7 - Developer-wise AI Usable JIRA %
    color_map = {
    'Total_Tickets': "#2a97a5",  # A nice green
    'AI_Applicable': "#94de85",       # A light green
    'AI_Not_Applicable': '#d62728'        # A standard red
    }
    sprint_group = df.groupby('Developer Name').agg(
        Total_Tickets=('Story Number', 'count'),
        AI_Applicable=('Copilot Implemented', lambda x: (x == 'yes').sum()),
        AI_Not_Applicable=('Copilot Implemented', lambda x: (x != 'yes').sum())
    ).reset_index()
    melted = pd.melt(sprint_group, id_vars='Developer Name', value_vars=['Total_Tickets', 'AI_Applicable','AI_Not_Applicable'])
    fig7, ax7 = plt.subplots(figsize=(10, 4))
    sns.barplot(data=melted, x='Developer Name', y='value', hue='variable', ax=ax7,palette=color_map)
    ax7.set_title("Developer-wise: Total Tickets vs AI Applied vs AI Not Applied")
    ax7.set_ylabel("Count")
    ax7.set_xlabel("Developer")
    ax7.bar_label(ax7.containers[0], padding=3)
    plt.xticks(rotation=45, ha='right')

    for container in ax7.containers:
        ax7.bar_label(container, padding=3)

    # dev_summary = df.groupby('Developer Name').agg(
    #         Total_Stories=('Story Number', 'count'),
    #         AI_Stories=('Copilot Implemented', lambda x: (x.str.lower() == 'yes').sum())
    #     ).reset_index()

    # dev_summary['AI_Adoption_Percentage'] = dev_summary.apply(
    #     lambda row: (row['AI_Stories'] / row['Total_Stories']) * 100 if row['Total_Stories'] > 0 else 0,
    #     axis=1
    # )
    # dev_summary = dev_summary.sort_values('AI_Adoption_Percentage', ascending=False)
    # fig7, ax7 = plt.subplots(figsize=(10, 4))
    # # sns.barplot(x=dev_summary.index, y=dev_summary.values, ax=ax7)
    # sns.barplot(
    #         data=dev_summary, 
    #         x='Developer Name', 
    #         y='AI_Adoption_Percentage', 
    #         ax=ax7, 
    #     )
    # ax7.set_ylabel("Average Jira %")
    # ax7.set_xlabel("Developer")
    # ax7.set_xticklabels(dev_summary['Developer Name'], rotation=45, ha='right')
    # ax7.set_title("Coplilot implemetaion % by developer")
    # ax7.bar_label(ax7.containers[0], fmt='%.1f', padding=3)
    
    
    # Chart 8 - Sprint-wise: Total Tickets vs AI Use Applied Line Graph
    sprint_group = df.groupby('Sprint').agg(
        Total_Stories=('Story Number', 'count'),
        AI_Stories=('Copilot Implemented', lambda x: (x.str.lower() == 'yes').sum())
    ).reset_index()
    
    sprint_group = sprint_group.sort_values('Sprint')
    melted = pd.melt(
        sprint_group, 
        id_vars='Sprint', 
        value_vars=['Total_Stories', 'AI_Stories'],
        var_name='Metric',
        value_name='Count'
    )

    fig8, ax8 = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=melted, 
        x='Sprint', 
        y='Count', 
        hue='Metric', 
        style='Metric', # Optional: gives different line styles (e.g., solid, dashed)
        markers=True,    # Adds markers (e.g., circles, 'x') at each data point
        dashes=True,     # Activates the 'style' parameter
        ax=ax8
    )
    ax8.set_title("Sprint-wise Tickets vs AI Use Applied")
    ax8.set_ylabel("Number of Stories")
    ax8.set_xlabel("Sprint")
    ax8.grid(True, which='both', linestyle='--', linewidth=0.5) # Enhance grid for readability
    plt.xticks(rotation=45, ha='right') # Rotate x-axis labels if they overlap

    for line in ax8.lines:
        for x, y in zip(line.get_xdata(), line.get_ydata()):
            ax8.text(x, y, f' {int(y)}', va='bottom', ha='left')        
        
    col7, col8 = st.columns(2)
    with col7:
        render_chart(fig7, "Chart 7: Developer-wise: Total Tickets vs AI Applied vs AI Not Applied", "chart7")
    with col8:
        render_chart(fig8, "Chart 8: Sprint-wise Tickets vs AI Use", "chart8")
