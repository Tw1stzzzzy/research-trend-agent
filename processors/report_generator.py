from datetime import datetime
import os
import json
from processors.trend_analyzer import analyze_trends
from processors.llm_summary import generate_llm_summary

def generate_report(scored_json_path, output_dir):
    """
    Read scored_papers.json and generate a comprehensive English Markdown report saved to output_dir/report.md.
    Report includes:
      1. Statistical data table
      2. Keyword distribution chart (if file exists)
      3. LLM-generated summary
      4. Specific paper recommendations
    Returns Markdown text content.
    """
    stats = analyze_trends(scored_json_path)
    if not stats:
        return ""

    # Load papers data for detailed recommendations
    with open(scored_json_path, "r", encoding="utf-8") as f:
        papers_data = json.load(f)

    # 1. Generate statistical text section
    report_lines = []
    report_lines.append(f"# AI Research Trend Report ({datetime.now().strftime('%Y-%m-%d')})\n")
    
    # Executive Summary
    report_lines.append("## Executive Summary\n")
    report_lines.append(f"- **Total Papers**: {stats['total_papers']}")
    report_lines.append(f"- **Open Source Papers**: {stats['open_source_count']} ({stats['open_source_count']/stats['total_papers']:.2%})")
    report_lines.append(f"- **Average Recognition Score**: {stats['avg_score']:.2f}\n")

    # Keyword Distribution
    report_lines.append("## Research Topics Distribution\n")
    if stats['keyword_counts']:
        # Sort keywords by count for better presentation
        sorted_keywords = sorted(stats['keyword_counts'].items(), key=lambda x: x[1], reverse=True)
        for kw, cnt in sorted_keywords:
            if cnt > 0:  # Only show keywords with papers
                report_lines.append(f"- **{kw.title()}**: {cnt} papers ({cnt/stats['total_papers']:.1%})")
    report_lines.append("")

    # 2. Paper Recommendations Section
    if papers_data:
        report_lines.append("## 📚 Recommended Papers\n")
        
        # Sort papers by score (highest first)
        sorted_papers = sorted(papers_data, key=lambda x: x.get('score', 0), reverse=True)
        
        for i, paper in enumerate(sorted_papers[:10], 1):  # Top 10 papers
            title = paper.get('title', 'N/A')
            authors = paper.get('authors', [])
            venue = paper.get('venue', 'N/A')
            score = paper.get('score', 0)
            summary = paper.get('summary', '')
            pdf_url = paper.get('pdf_url', '')
            repo = paper.get('repo', '')
            stars = paper.get('stars', 0)
            
            # Format authors (limit to first 3)
            author_str = ', '.join(authors[:3])
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"
            
            report_lines.append(f"### {i}. {title}")
            report_lines.append(f"**Authors**: {author_str}")
            report_lines.append(f"**Venue**: {venue} | **Score**: {score:.1f}")
            
            if repo and repo != "null":
                repo_info = f"🔗 [GitHub]({repo})"
                if stars and stars > 0:
                    repo_info += f" ({stars:,} ⭐)"
                report_lines.append(f"**Repository**: {repo_info}")
            
            if pdf_url and pdf_url != "#":
                report_lines.append(f"**PDF**: [Download]({pdf_url})")
            
            if summary and summary.strip():
                report_lines.append(f"**Summary**: {summary}")
            else:
                # Generate a brief description based on title
                report_lines.append(f"**Research Focus**: {_generate_focus_from_title(title)}")
                
            report_lines.append("")  # Empty line between papers
        
        report_lines.append("")

    # 3. Insert visualization chart (if keyword_trend.png exists)
    fig_path = os.path.join(output_dir, "keyword_trend.png")
    if os.path.exists(fig_path):
        report_lines.append("## Keyword Trend Visualization")
        report_lines.append("![Keyword Distribution](keyword_trend.png)\n")

    # 4. Generate LLM analysis
    llm_text = generate_llm_summary(stats)
    report_lines.append("## AI-Generated Analysis")
    report_lines.append(llm_text)
    report_lines.append("")

    # 5. Additional metrics (if applicable)
    if stats['total_papers'] > 0:
        report_lines.append("## Key Insights\n")
        
        # Open source rate analysis
        open_source_rate = stats['open_source_count']/stats['total_papers']
        if open_source_rate > 0.5:
            report_lines.append("✅ **High Open Source Adoption**: Over 50% of papers have open source implementations")
        elif open_source_rate > 0.3:
            report_lines.append("📊 **Moderate Open Source Adoption**: 30-50% of papers have open source implementations")
        else:
            report_lines.append("📉 **Low Open Source Adoption**: Less than 30% of papers have open source implementations")
        
        # Research activity assessment
        if stats['total_papers'] > 20:
            report_lines.append("🔥 **High Research Activity**: Significant number of relevant papers published")
        elif stats['total_papers'] > 10:
            report_lines.append("📈 **Moderate Research Activity**: Good volume of relevant publications")
        else:
            report_lines.append("📝 **Emerging Research Area**: Limited but focused publication activity")
        
        report_lines.append("")

    # 6. Footer with generation info
    report_lines.append("---")
    report_lines.append(f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by AI Research Agent*")

    report_text = "\n".join(report_lines)

    # Save Markdown file
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text

def _generate_focus_from_title(title):
    """
    Based on paper title, generate a brief research focus description
    """
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['transformer', 'attention', 'bert', 'gpt']):
        return "Transformer-based architecture for improved performance"
    elif any(word in title_lower for word in ['diffusion', 'generative', 'gan']):
        return "Generative modeling and image synthesis"
    elif any(word in title_lower for word in ['detection', 'segmentation', 'classification']):
        return "Computer vision and object recognition"
    elif any(word in title_lower for word in ['graph', 'network', 'neural']):
        return "Neural network architecture and graph learning"
    elif any(word in title_lower for word in ['quantization', 'compression', 'efficient']):
        return "Model optimization and efficiency improvements"
    else:
        return "Novel approach to machine learning challenges"
