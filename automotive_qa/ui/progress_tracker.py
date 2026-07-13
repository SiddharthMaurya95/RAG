import streamlit as st
import time

class ProgressTracker:
    """
    Enterprise Execution Progress Tracker for Streamlit.
    Displays a real-time, stage-based progress interface without triggering full app reruns.
    """
    def __init__(self, stages: list[str], title: str = "Processing Request"):
        self.stages = stages
        self.title = title
        self.current_stage_idx = 0
        self.start_time = time.time()
        self.metrics = {}
        self.status = "running" # "running", "completed", "failed"
        self.error_msg = None
        self.failed_stage_name = None
        self.stage_info = {} # mapping of stage_name to info text
        self.container = st.empty()
        
        # Timing per stage
        self.stage_times = {}
        self.current_stage_start = time.time()
        
        self._render()
        
    def start_stage(self, stage_name: str):
        """Advances the tracker to the given stage."""
        if self.status == "failed":
            return
            
        if stage_name in self.stages:
            idx = self.stages.index(stage_name)
            if idx >= self.current_stage_idx:
                self.current_stage_idx = idx
                self.current_stage_start = time.time()
        self._render()
        
    def complete_stage(self, stage_name: str, info_text: str = None):
        """Marks a stage as completed and moves to the next."""
        if self.status == "failed":
            return
            
        elapsed = time.time() - self.current_stage_start
        self.stage_times[stage_name] = elapsed
        
        if info_text:
            self.stage_info[stage_name] = info_text
            
        if stage_name in self.stages:
            idx = self.stages.index(stage_name)
            if idx == self.current_stage_idx:
                self.current_stage_idx += 1
                self.current_stage_start = time.time()
        self._render()
        
    def add_metric(self, key: str, value):
        """Adds a metric to the final execution summary."""
        self.metrics[key] = value
        
    def fail_stage(self, stage_name: str, error_msg: str):
        """Halts execution and displays an error message."""
        self.status = "failed"
        self.failed_stage_name = stage_name
        self.error_msg = error_msg
        
        elapsed = time.time() - self.current_stage_start
        self.stage_times[stage_name] = elapsed
        
        self._render()
        
    def finish(self, metrics: dict = None):
        """Marks execution as fully complete and displays the summary."""
        if self.status == "failed":
            return
            
        self.status = "completed"
        self.current_stage_idx = len(self.stages)
        if metrics:
            self.metrics.update(metrics)
            
        self.metrics["Total execution time"] = f"{(time.time() - self.start_time):.2f}s"
        
        self._render()

    def _render(self):
        """Renders the HTML/CSS for the tracker inside the Streamlit container."""
        with self.container.container():
            st.markdown(f"#### {self.title}")
            
            # Progress bar
            progress_val = min(self.current_stage_idx / max(len(self.stages), 1), 1.0)
            st.progress(progress_val)
            
            # Stages UI
            html = "<div style='font-family: Inter, sans-serif; font-size: 14px; margin-bottom: 10px; color: #334155; padding: 12px 16px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);'>"
            
            for i, stage in enumerate(self.stages):
                if self.status == "failed" and stage == self.failed_stage_name:
                    icon = "❌"
                    color = "#ef4444"
                    status_text = "Failed"
                elif i < self.current_stage_idx:
                    icon = "✓"
                    color = "#10b981"
                    status_text = "Completed"
                elif i == self.current_stage_idx and self.status == "running":
                    icon = "⏳"
                    color = "#0ea5e9"
                    status_text = "Current"
                else:
                    icon = "○"
                    color = "#cbd5e1"
                    status_text = "Pending"
                    
                weight = "600" if status_text == "Current" else "500"
                text_color = "#0f172a" if status_text in ["Completed", "Current", "Failed"] else "#94a3b8"
                
                html += f"<div style='margin-bottom: 8px; display: flex; flex-direction: column;'>"
                html += f"<div style='display: flex; align-items: center;'><span style='color: {color}; font-weight: 600; margin-right: 12px; width: 16px; display: inline-block; text-align: center; font-size: 15px;'>{icon}</span>"
                html += f"<span style='color: {text_color}; font-weight: {weight}; letter-spacing: -0.01em;'>{stage}</span></div>"
                
                if stage in self.stage_info:
                    html += f"<div style='margin-left: 28px; font-size: 13px; color: #64748b; margin-top: 2px;'>{self.stage_info[stage]}</div>"
                    
                html += "</div>"
                
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
            
            if self.status == "failed":
                st.error(f"Execution Failed at **{self.failed_stage_name}**: {self.error_msg}")
            elif self.status == "completed":
                # Render summary
                st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
                st.markdown("**Execution Summary**")
                
                # Arrange metrics in columns
                metric_keys = list(self.metrics.keys())
                
                # Split metrics into two columns
                cols = st.columns(2)
                for i, k in enumerate(metric_keys):
                    val = self.metrics[k]
                    with cols[i % 2]:
                        st.markdown(f"<div style='font-size: 13px; margin-bottom: 6px;'><span style='color: #64748b;'>{k}:</span> <span style='font-weight: 600; color: #0f172a;'>{val}</span></div>", unsafe_allow_html=True)
                        
                st.markdown("</div>", unsafe_allow_html=True)
