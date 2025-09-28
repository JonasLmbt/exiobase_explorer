from __future__ import annotations

from typing import Dict, Callable, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QComboBox, QHBoxLayout, QDialog, QLabel, QCheckBox, QDialogButtonBox, QVBoxLayout, QSpinBox, QDoubleSpinBox, QPushButton, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt


class MethodSelectorWidget(QWidget):
    """
    One-line drop-down to select an analysis method.

    - Shows localized labels (via `tr`).
    - Keeps stable `method_id` in userData.
    - Emits methodChanged(method_id) on change.
    """
    methodChanged = pyqtSignal(str)

    def __init__(self, methods: Dict[str, object], tr: Callable[[str, str], str], parent=None):
        super().__init__(parent)
        self._methods = methods
        self._tr = tr

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox(self)
        for mid, m in self._methods.items():
            label = self._tr(getattr(m, "label", str(mid)), getattr(m, "label", str(mid)))
            self.combo.addItem(label, userData=mid)
        self.combo.currentIndexChanged.connect(self._emit_change)
        layout.addWidget(self.combo)

    def _emit_change(self, *_):
        mid = self.combo.currentData()
        if mid:
            self.methodChanged.emit(mid)

    def set_current_method(self, method_id: str) -> None:
        idx = self.combo.findData(method_id)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def current_method(self) -> str:
        return self.combo.currentData()

    def current_label(self) -> str:
        return self.combo.currentText()


class ImpactSelectorWidget(QWidget):
    """
    One-line impact selector.

    - Displays localized labels (via `tr`), keeps raw impact names in userData.
    - current_value(): raw impact name
    - current_display(): localized display text
    """
    impactChanged = pyqtSignal(str)

    def __init__(self, impacts: list[str], tr: Callable[[str, str], str],
                 include_subcontractors: bool = True, parent=None):
        super().__init__(parent)
        self._tr = tr

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox(self)

        if include_subcontractors:
            raw = "Subcontractors"
            self.combo.addItem(self._tr(raw, raw), userData=raw)

        for imp in impacts:
            self.combo.addItem(self._tr(imp, imp), userData=imp)

        self.combo.currentIndexChanged.connect(self._emit_change)
        layout.addWidget(self.combo)

    def _emit_change(self, *_):
        val = self.current_value()
        if val is not None:
            self.impactChanged.emit(val)

    def set_current_impact(self, impact_name: str) -> None:
        idx = self.combo.findData(impact_name)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def current_value(self) -> str:
        return self.combo.currentData()

    def current_display(self) -> str:
        return self.combo.currentText()


class WorldMapSettingsDialog(QDialog):
    """
    Comprehensive settings dialog for the World Map method.

    Exposes:
      - Colormap (color)
      - Relative normalization (relative)
      - Legend visibility (show_legend)
      - Title (title)

      Classification:
        - mode: "binned" | "continuous"
        - k: number of classes (binned)
        - custom_bins: explicit breaks (comma-separated floats; overrides 'k' if provided)
        - norm_mode (continuous): "linear" | "log" | "power"
        - robust (continuous): quantile clipping in %, e.g. 2 -> [2%, 98%]
        - gamma (continuous): gamma for PowerNorm

      Advanced (stored for future use / overlays):
        - draw_borders (bool)
        - label_density (int)
        - projection (str)

    The dialog is initialized with a settings dict and will return an updated
    settings dict via `get_settings()`.
    """

    def __init__(self, settings: dict, tr: Callable[[str, str], str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("World Map Settings", "World Map Settings"))
        self.setModal(True)
        self._tr = tr

        # --- Current state (copy to avoid mutating caller until accepted) ---
        self._settings = dict(settings or {})

        v = QVBoxLayout(self)

        # --- Basic ---
        # Colormap
        v.addWidget(QLabel(tr("Colormap", "Colormap")))
        self.cmap = QComboBox(self)
        for cm in ["Reds", "Blues", "Greens", "Purples", "Oranges", "viridis", "plasma", "magma", "cividis"]:
            self.cmap.addItem(cm)
        self.cmap.setCurrentText(self._settings.get("color", "Reds"))
        v.addWidget(self.cmap)

        # Legend
        self.legend = QCheckBox(tr("Show legend", "Show legend"), self)
        self.legend.setChecked(bool(self._settings.get("show_legend", False)))
        v.addWidget(self.legend)

        # Title
        v.addWidget(QLabel(tr("Title (optional)", "Title (optional)")))
        self.title = QComboBox(self)  # use editable combo for quick reuse
        self.title.setEditable(True)
        self.title.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.title.setCurrentText(self._settings.get("title", "") or "")
        v.addWidget(self.title)

        # --- Classification ---
        v.addWidget(QLabel(tr("Classification", "Classification")))
        row1 = QHBoxLayout()
        v.addLayout(row1)

        self.mode = QComboBox(self)
        self.mode.addItems(["binned", "continuous"])
        self.mode.setCurrentText(self._settings.get("mode", "binned"))
        row1.addWidget(QLabel(tr("Mode", "Mode")))
        row1.addWidget(self.mode)

        # Binned controls
        row_binned = QHBoxLayout()
        v.addLayout(row_binned)
        row_binned.addWidget(QLabel(tr("Classes (k)", "Classes (k)")))
        self.k = QSpinBox(self)
        self.k.setRange(2, 12)
        self.k.setValue(int(self._settings.get("k", 7)))
        row_binned.addWidget(self.k)

        row_bins = QHBoxLayout()
        v.addLayout(row_bins)
        row_bins.addWidget(QLabel(tr("Custom bins (comma-separated)", "Custom bins (comma-separated)")))
        self.custom_bins = QComboBox(self)
        self.custom_bins.setEditable(True)
        self.custom_bins.setCurrentText(self._format_bins_for_edit(self._settings.get("custom_bins")))
        row_bins.addWidget(self.custom_bins)

        # Continuous controls
        v.addWidget(QLabel(tr("Normalization (continuous mode)", "Normalization (continuous mode)")))
        row_norm = QHBoxLayout()
        v.addLayout(row_norm)

        self.norm_mode = QComboBox(self)
        self.norm_mode.addItems(["linear", "log", "power"])
        self.norm_mode.setCurrentText(self._settings.get("norm_mode", "linear"))
        row_norm.addWidget(QLabel(tr("Norm", "Norm")))
        row_norm.addWidget(self.norm_mode)

        row_robust = QHBoxLayout()
        v.addLayout(row_robust)
        row_robust.addWidget(QLabel(tr("Robust clipping (%)", "Robust clipping (%)")))
        self.robust = QDoubleSpinBox(self)
        self.robust.setSuffix(" %")
        self.robust.setRange(0.0, 20.0)
        self.robust.setSingleStep(0.5)
        self.robust.setValue(float(self._settings.get("robust", 2.0)))
        row_robust.addWidget(self.robust)

        row_gamma = QHBoxLayout()
        v.addLayout(row_gamma)
        row_gamma.addWidget(QLabel(tr("Gamma (power norm)", "Gamma (power norm)")))
        self.gamma = QDoubleSpinBox(self)
        self.gamma.setRange(0.1, 5.0)
        self.gamma.setSingleStep(0.1)
        self.gamma.setValue(float(self._settings.get("gamma", 0.7)))
        row_gamma.addWidget(self.gamma)

        # Enable/disable controls depending on mode
        def _refresh_visibility():
            is_binned = self.mode.currentText() == "binned"
            self.k.setEnabled(is_binned)
            self.custom_bins.setEnabled(is_binned)
            is_cont = not is_binned
            self.norm_mode.setEnabled(is_cont)
            self.robust.setEnabled(is_cont)
            self.gamma.setEnabled(is_cont)

        self.mode.currentIndexChanged.connect(_refresh_visibility)
        _refresh_visibility()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    # ----------------- helpers -----------------
    def _format_bins_for_edit(self, bins):
        if not bins:
            return ""
        try:
            return ", ".join(str(float(b)) for b in bins)
        except Exception:
            return str(bins)

    def _parse_bins(self) -> Optional[list]:
        text = self.custom_bins.currentText().strip()
        if not text:
            return None
        try:
            parts = [p.strip() for p in text.replace(";", ",").split(",")]
            vals = [float(p) for p in parts if p]
            return vals if vals else None
        except Exception:
            # Silently ignore malformed bins → caller will fallback to k
            return None

    def get_settings(self) -> dict:
        """Return a dict of all settings for the world map method."""
        return {
            "color": self.cmap.currentText(),
            "show_legend": self.legend.isChecked(),
            "title": self.title.currentText().strip() or "",
            "mode": self.mode.currentText(),
            "k": int(self.k.value()),
            "custom_bins": self._parse_bins(),
            "norm_mode": self.norm_mode.currentText(),
            "robust": float(self.robust.value()),
            "gamma": float(self.gamma.value()),
        }


class ImpactMultiSelectorButton(QWidget):
    """
    Compact one-line multi-impact selector with a button that opens a tree dialog.

    Usage:
      - Instantiate with a nested impact hierarchy (dict[str, dict, ...]).
      - Call set_defaults(list[str]) to define initially selected impacts.
      - Connect to impactsChanged(list[str]) to react to changes.
      - The button text shows "Selected (n)".
    """
    impactsChanged = pyqtSignal(list)

    def __init__(self, nested_hierarchy: Dict, tr, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tr = tr  # translation callable
        self._hierarchy = nested_hierarchy or {}
        self._selected = set()
        self._defaults = set()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton(self)
        self.btn.clicked.connect(self._open_dialog)
        lay.addWidget(self.btn)

        self._update_button_text()

    def set_defaults(self, defaults: List[str]) -> None:
        """Define default selection; also sets current selection to these defaults."""
        self._defaults = set(defaults or [])
        self._selected = set(defaults or [])
        self._update_button_text()

    def selected_impacts(self) -> List[str]:
        """Return the current selection as a list (order not guaranteed)."""
        return list(self._selected)

    def set_selected_impacts(self, impacts: List[str]) -> None:
        self._selected = set(impacts or [])
        self._update_button_text()
        self.impactsChanged.emit(self.selected_impacts())

    # ---------------- internal ----------------
    def _update_button_text(self) -> None:
        count = len(self._selected)
        self.btn.setText(f"{self._tr('Selected', 'Selected')} ({count})")

    def _open_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("Select Impacts", "Select Impacts"))
        dlg.setMinimumSize(350, 300)
        v = QVBoxLayout(dlg)

        v.addWidget(QLabel(f"{self._tr('Select Impacts', 'Select Impacts')}:"))

        tree = QTreeWidget(dlg)
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QTreeWidget.NoSelection)
        v.addWidget(tree)

        # populate
        def add_items(parent_item, data_dict, level=0):
            for key, val in data_dict.items():
                item = QTreeWidgetItem(parent_item)
                # store raw key, display localized text
                item.setData(0, Qt.UserRole + 1, key)
                item.setText(0, self._tr(key, key))
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(0, Qt.Checked if key in self._selected else Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_items(item, val, level + 1)
                    
        add_items(tree, self._hierarchy)

        # buttons row
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        row = QHBoxLayout()
        reset_btn = QPushButton(self._tr("Reset to Defaults", "Reset to Defaults"), dlg)
        reset_btn.clicked.connect(lambda: self._reset_to_defaults(tree))
        row.addWidget(reset_btn)
        row.addStretch(1)
        row.addWidget(buttons)
        v.addLayout(row)

        buttons.accepted.connect(lambda: self._accept_dialog(tree, dlg))
        buttons.rejected.connect(dlg.reject)

        dlg.exec_()

    def _reset_to_defaults(self, tree: QTreeWidget):
        def walk(item: QTreeWidgetItem):
            raw = item.data(0, Qt.UserRole + 1)
            item.setCheckState(0, Qt.Checked if raw in self._defaults else Qt.Unchecked)
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i))

    def _accept_dialog(self, tree: QTreeWidget, dlg: QDialog):
        new_sel = set()
        def collect(item: QTreeWidgetItem):
            raw = item.data(0, Qt.UserRole + 1)
            if raw is not None and (item.flags() & Qt.ItemIsUserCheckable) and item.checkState(0) == Qt.Checked:
                new_sel.add(raw)
            for i in range(item.childCount()):
                collect(item.child(i))
        for i in range(tree.topLevelItemCount()):
            collect(tree.topLevelItem(i))

        self._selected = new_sel
        self._update_button_text()
        self.impactsChanged.emit(self.selected_impacts())
        dlg.accept()