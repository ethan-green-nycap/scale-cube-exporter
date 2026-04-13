"""
Desktop UI for Scale Cube Exporter — built with Flet 0.83+.

Dark theme, minimal design. Select multiple OBJ files, choose cube size,
run Blender 3.6 headless to add a reference scale cube beneath each model.
"""

import asyncio
import threading
from pathlib import Path

import flet as ft
from flet import Clipboard

from core.exporter import CUBE_SIZES, DEFAULT_BLENDER, process_obj
from ui.file_picker import pick_obj_files, pick_exe_file


class ObjItem(ft.Container):
    """A single OBJ file row in the queue."""

    def __init__(self, path: Path, on_remove):
        self.obj_path = path
        self.obj_name = path.name
        self.is_done = False

        self.status_text = ft.Text(
            "Ready",
            size=11,
            color=ft.Colors.WHITE38,
        )
        self.progress_detail = ft.Text("", size=11, color=ft.Colors.TEAL_400)

        self._remove_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=14,
            icon_color=ft.Colors.WHITE24,
            on_click=lambda _: on_remove(self),
            tooltip="Remove",
        )

        super().__init__(
            content=ft.Row(
                controls=[
                    ft.Text(self.obj_name, size=13, expand=True),
                    self.status_text,
                    self.progress_detail,
                    self._remove_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            margin=ft.margin.only(bottom=6),
        )

    def set_running(self, message: str, detail: str = ""):
        self.status_text.value = message
        self.status_text.color = ft.Colors.WHITE54
        self.progress_detail.value = detail
        self._remove_btn.visible = False

    def set_done(self, elapsed: float):
        self.is_done = True
        self.status_text.value = "Done"
        self.status_text.color = ft.Colors.TEAL_400
        self.progress_detail.value = f"{elapsed}s"
        self._remove_btn.visible = False

    def set_error(self, message: str):
        self.is_done = True
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED_400
        self.progress_detail.value = ""
        self._remove_btn.visible = False


async def build_app(page: ft.Page):
    page.title = "Scale Cube Exporter"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1a1a1a"
    page.padding = 30
    page.window.width = 560
    page.window.height = 720

    def push_update():
        """Thread-safe UI update via Flet's async event loop."""
        async def _do_update():
            page.update()
        page.run_task(_do_update)

    obj_items: list[ObjItem] = []
    all_paths: set[str] = set()
    is_running = False

    APP_DIR = Path(__file__).resolve().parent.parent
    BLENDER_SCRIPT = APP_DIR / "blender_script.py"

    # --- Controls ---

    cube_dropdown = ft.Dropdown(
        label="Cube Size",
        value="1 cm  (0.01 m)",
        options=[ft.dropdown.Option(label) for label in CUBE_SIZES],
        width=180,
        dense=True,
        border_color=ft.Colors.WHITE10,
        focused_border_color=ft.Colors.TEAL_400,
    )

    blender_field = ft.TextField(
        label="Blender Executable",
        value=str(DEFAULT_BLENDER),
        text_size=11,
        dense=True,
        border_color=ft.Colors.WHITE10,
        focused_border_color=ft.Colors.TEAL_400,
        expand=True,
    )

    # Blender exe picker (native dialog in thread)
    async def browse_blender(_):
        path = await asyncio.to_thread(
            pick_exe_file,
            title="Locate blender.exe",
            initial_dir=r"C:\Program Files",
        )
        if path:
            blender_field.value = str(path)
            page.update()

    blender_browse_btn = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        icon_size=18,
        icon_color=ft.Colors.WHITE38,
        on_click=browse_blender,
        tooltip="Browse for blender.exe",
    )

    # OBJ file picker (native dialog in thread)
    async def add_files(_):
        paths = await asyncio.to_thread(
            pick_obj_files,
            title="Select OBJ files",
            initial_dir=r"C:\Clients",
        )
        if not paths:
            return

        added = 0
        for p in paths:
            key = str(p)
            if key not in all_paths:
                item = ObjItem(p, on_remove=remove_item)
                obj_items.append(item)
                file_list.controls.append(item)
                all_paths.add(key)
                added += 1

        if added == 0:
            status_bar.value = "No new files to add"
            status_bar.color = ft.Colors.AMBER_400
        else:
            status_bar.value = f"Added {added} OBJ file{'s' if added != 1 else ''}"
            status_bar.color = ft.Colors.TEAL_400
        update_status()

    file_list = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    status_bar = ft.Text("", size=12, color=ft.Colors.WHITE54)

    # --- Log panel ---

    log_column = ft.Column(spacing=1, scroll=ft.ScrollMode.AUTO)
    log_panel = ft.Container(
        content=log_column,
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border_radius=8,
        padding=ft.padding.all(10),
        height=140,
        visible=False,
    )

    log_colors = {
        "info": ft.Colors.WHITE38,
        "success": ft.Colors.TEAL_400,
        "warning": ft.Colors.AMBER_400,
        "error": ft.Colors.RED_400,
    }
    log_lines: list[str] = []

    def log(message: str, detail: str = "", level: str = "info"):
        text = message
        if detail:
            text += f"  {detail}"
        prefix = {"info": "    ", "success": " OK ", "warning": "WARN", "error": " ERR"}
        log_lines.append(f"[{prefix.get(level, '    ')}] {text}")
        log_column.controls.append(
            ft.Text(text, size=11, color=log_colors.get(level, ft.Colors.WHITE38))
        )

    def clear_log():
        log_column.controls.clear()
        log_lines.clear()
        log_panel.visible = False

    async def copy_log(_):
        text = "\n".join(log_lines)
        await Clipboard().set(text)
        copy_log_btn.icon = ft.Icons.CHECK
        copy_log_btn.icon_color = ft.Colors.TEAL_400
        page.update()
        await asyncio.sleep(1.5)
        copy_log_btn.icon = ft.Icons.COPY
        copy_log_btn.icon_color = ft.Colors.WHITE24
        page.update()

    copy_log_btn = ft.IconButton(
        icon=ft.Icons.COPY,
        icon_size=14,
        icon_color=ft.Colors.WHITE24,
        on_click=copy_log,
        tooltip="Copy log to clipboard",
    )

    def update_status():
        count = len(obj_items)
        if count == 0:
            status_bar.value = ""
        else:
            status_bar.value = f"{count} OBJ file{'s' if count != 1 else ''}"
        page.update()

    # --- Item management ---

    def remove_item(item: ObjItem):
        if is_running:
            return
        all_paths.discard(str(item.obj_path))
        obj_items.remove(item)
        file_list.controls.remove(item)
        update_status()

    # --- Run ---

    run_btn = ft.ElevatedButton(
        "Run",
        icon=ft.Icons.PLAY_ARROW,
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.TEAL_700,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        height=42,
    )

    add_btn = ft.ElevatedButton(
        "Add Files",
        icon=ft.Icons.ADD,
        color=ft.Colors.WHITE70,
        bgcolor=ft.Colors.WHITE10,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        height=42,
        on_click=add_files,
    )

    def start_processing(_):
        nonlocal is_running
        if is_running or not obj_items:
            return
        is_running = True
        run_btn.disabled = True
        add_btn.disabled = True
        page.update()
        threading.Thread(target=run_all, daemon=True).start()

    run_btn.on_click = start_processing

    def run_all():
        nonlocal is_running

        clear_log()
        log_panel.visible = True
        push_update()

        blender_exe = Path(blender_field.value.strip())
        cube_label = cube_dropdown.value
        cube_size = CUBE_SIZES[cube_label]

        if not blender_exe.is_file():
            log(f"Blender not found: {blender_exe}", "", "error")
            status_bar.value = "Blender not found"
            status_bar.color = ft.Colors.RED_400
            is_running = False
            run_btn.disabled = False
            add_btn.disabled = False
            push_update()
            return

        if not BLENDER_SCRIPT.is_file():
            log(f"blender_script.py not found: {BLENDER_SCRIPT}", "", "error")
            status_bar.value = "blender_script.py missing"
            status_bar.color = ft.Colors.RED_400
            is_running = False
            run_btn.disabled = False
            add_btn.disabled = False
            push_update()
            return

        log(f"Cube size: {cube_label}", "", "info")
        log(f"Blender: {blender_exe}", "", "info")
        push_update()

        for i, item in enumerate(obj_items):
            if item.is_done:
                continue

            log(f"--- {item.obj_name} ({i + 1}/{len(obj_items)}) ---", "", "info")
            item.set_running("Running...", f"{i + 1}/{len(obj_items)}")
            push_update()

            def on_progress(message, detail, level, _item=item):
                _item.set_running(message)
                log(message, detail, level)
                push_update()

            result = process_obj(
                item.obj_path,
                cube_size,
                blender_exe,
                BLENDER_SCRIPT,
                on_progress=on_progress,
            )

            if "error" in result:
                item.set_error(result["error"])
                log(f"Error: {result['error']}", item.obj_name, "error")
            else:
                item.set_done(result["elapsed"])
                log(f"Done {item.obj_name}", f"{result['elapsed']}s", "success")
            push_update()

        is_running = False
        run_btn.disabled = False
        add_btn.disabled = False
        status_bar.value = "Done"
        status_bar.color = ft.Colors.TEAL_400
        push_update()

    # --- Layout ---

    page.add(
        ft.Column(
            controls=[
                ft.Text("Scale Cube Exporter", size=22, weight=ft.FontWeight.W_600),
                ft.Container(height=12),
                ft.Row(
                    controls=[
                        cube_dropdown,
                        ft.Container(expand=True),
                        add_btn,
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                ft.Row(
                    controls=[blender_field, blender_browse_btn],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=12),
                ft.Text("OBJ Files", size=13, color=ft.Colors.WHITE54),
                ft.Container(height=6),
                file_list,
                ft.Container(height=8),
                ft.Row(
                    controls=[
                        ft.Text("Log", size=13, color=ft.Colors.WHITE54),
                        ft.Container(expand=True),
                        copy_log_btn,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                log_panel,
                ft.Container(height=8),
                ft.Row(
                    controls=[status_bar, ft.Container(expand=True), run_btn],
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            expand=True,
            spacing=0,
        )
    )
