import chunk
from time import sleep
import flet
from flet import (
    AppBar,
    ElevatedButton,
    Page,
    Text,
    View,
    Row,
    ProgressRing,
    Column,
    FilePicker,
    FilePickerResultEvent,
    icons,
    ProgressBar,
    Banner,
    colors,
    TextButton,
    Icon,
    TextField,
)
from typing import List
from subprocess import check_output, STDOUT, call, CalledProcessError
from functools import partial

from installer_config import InstallerConfig


recovery_path = None
image_path = None


def main(page: Page):
    page.title = "OpenAndroidInstaller"
    page.window_width = 480
    page.window_height = 640
    page.window_top = 100
    page.window_left = 720
    # page.theme_mode = "dark"
    views = []
    pb = ProgressBar(width=400, color="amber", bgcolor="#eeeeee", bar_height=16)
    pb.value = 0
    num_views = None  # this is updated later
    inputtext = TextField(hint_text="your unlock code", expand=False)  # textfield for the unlock code

    # Click-event handlers

    def confirm(e):
        view_num = int(page.views[-1].route) + 1
        global num_views
        if num_views:
            pb.value = view_num / num_views
        page.views.clear()
        page.views.append(views[view_num])
        page.update()

    def close_banner(e):
        page.banner.open = False
        page.update()

    def search_devices(e):
        config_path = "openandroidinstaller/assets/configs/"
        try:
            # read device properties
            output = check_output(
                [
                    "adb",
                    "shell",
                    "dumpsys",
                    "bluetooth_manager",
                    "|",
                    "grep",
                    "'name:'",
                    "|",
                    "cut",
                    "-c9-",
                ],
                stderr=STDOUT,
            ).decode()
            page.views[-1].controls.append(Text(f"Detected: {output}"))
            # load config from file
            config = InstallerConfig.from_file(config_path + output.strip() + ".yaml")
            page.views[-1].controls.append(Text(f"Installer configuration found."))
            page.views[-1].controls.append(
                ElevatedButton(
                    "Confirm and continue",
                    on_click=confirm,
                    icon=icons.NEXT_PLAN_OUTLINED,
                )
            )
            new_views = views_from_config(config)
            views.extend(new_views)
            global num_views
            num_views = len(views)
        except CalledProcessError:
            output = "No device detected!"
            page.views[-1].controls.append(Text(f"{output}"))
        page.update()

    def views_from_config(config: InstallerConfig) -> List[View]:
        new_views = []
        # create a view for every step
        for num_step, step in enumerate(config.steps):
            step_content = []
            # basic view depending on step.type
            if step.type == "confirm_button":
                step_content=[confirm_button(step.content)]
            elif step.type == "call_button":
                step_content=[call_button(step.content, command=step.command)]
            elif step.type == "call_button_with_input":
                step_content=[inputtext, call_button(step.content, command=step.command)]
            elif step.type == "text":
                step_content = [Text(step.content)]
            else:
                raise Exception(f"Unknown step type: {step.type}")

            # if skipping is allowed add a button to the view
            if step.allow_skip:
                step_content.append(confirm_button("Already done?", confirm_text="Skip"))
            
            # append the new view
            new_views.append(
                get_new_view(
                    title=step.title,
                    content=step_content,
                    index=2 + num_step,
                )
            )
        return new_views

    def call_to_phone(e, command: str):
        command = command.replace("recovery", recovery_path)
        command = command.replace("image", image_path)
        command = command.replace("inputtext", inputtext.value)
        page.views[-1].controls.append(ProgressRing())
        page.update()
        res = call(f"{command}", shell=True)
        if res != 0:
            page.views[-1].controls.pop()
            page.views[-1].controls.append(Text("Command {command} failed!"))
        else:
            sleep(5)
            page.views[-1].controls.pop()
            page.views[-1].controls.append(
                ElevatedButton("Confirm and continue", on_click=confirm)
            )
        page.update()

    # file picker setup

    def pick_image_result(e: FilePickerResultEvent):
        selected_image.value = (
            ", ".join(map(lambda f: f.name, e.files)) if e.files else "Cancelled!"
        )
        global image_path
        image_path = e.files[0].path
        selected_image.update()

    def pick_recovery_result(e: FilePickerResultEvent):
        selected_recovery.value = (
            ", ".join(map(lambda f: f.name, e.files)) if e.files else "Cancelled!"
        )
        global recovery_path
        recovery_path = e.files[0].path
        selected_recovery.update()

    pick_image_dialog = FilePicker(on_result=pick_image_result)
    pick_recovery_dialog = FilePicker(on_result=pick_recovery_result)
    selected_image = Text()
    selected_recovery = Text()
    page.overlay.append(pick_image_dialog)
    page.overlay.append(pick_recovery_dialog)

    # warnings banner

    page.banner = Banner(
        bgcolor=colors.AMBER_100,
        leading=Icon(icons.WARNING_AMBER_ROUNDED, color=colors.AMBER, size=40),
        content=Text(
            "Important: Please read through the instructions at least once before actually following them, so as to avoid any problems due to any missed steps!"
        ),
        actions=[
            TextButton("I understand", on_click=close_banner),
        ],
    )

    # Generate the Views for the different steps

    def confirm_button(text: str, confirm_text: str = "Confirm and continue") -> Row:
        words = text.split(" ")
        chunk_size = 10
        if len(words) > chunk_size:
            n_chunks = len(words) // chunk_size
            text_field = [
                Text(f"{' '.join(words[i*chunk_size:(i+1)*chunk_size])}")
                for i in range(n_chunks)
            ]
            return Column(
                text_field
                + [
                    ElevatedButton(
                        f"{confirm_text}",
                        on_click=confirm,
                        icon=icons.NEXT_PLAN_OUTLINED,
                    )
                ]
            )
        else:
            text_field = Text(f"{text}")
            return Row(
                [
                    text_field,
                    ElevatedButton(
                        f"{confirm_text}",
                        on_click=confirm,
                        icon=icons.NEXT_PLAN_OUTLINED,
                    ),
                ]
            )

    def call_button(
        text: str, command: str, confirm_text: str = "Confirm and run"
    ) -> Row:
        return Row(
            [
                Text(f"{text}"),
                ElevatedButton(
                    f"{confirm_text}", on_click=partial(call_to_phone, command=command)
                ),
            ]
        )

    def get_new_view(title: str, index: int, content: List = []) -> View:
        title_bar = AppBar(
            leading=Icon(icons.ANDROID_OUTLINED),
            leading_width=40,
            center_title=True,
            elevation=16,
        )
        if index != 0:
            title_bar.title = Text(f"Step {index}: {title}")
        else:
            title_bar.title = Text(f"{title}")
        return View(
            route=f"{index}",
            controls=[pb] + content,
            padding=50,
            appbar=title_bar,
            floating_action_button=None,
        )

    # main part

    views = [
        get_new_view(
            title="Welcome to OpenAndroidInstaller!",
            content=[
                ElevatedButton(
                    "Search device", on_click=search_devices, icon=icons.PHONE_ANDROID
                )
            ],
            index=0,
        ),
        get_new_view(
            title="Pick image and recovery",
            content=[
                Row(
                    [
                        ElevatedButton(
                            "Pick image file",
                            icon=icons.UPLOAD_FILE,
                            on_click=lambda _: pick_image_dialog.pick_files(
                                allow_multiple=False
                            ),
                        ),
                        selected_image,
                    ]
                ),
                Row(
                    [
                        ElevatedButton(
                            "Pick recovery file",
                            icon=icons.UPLOAD_FILE,
                            on_click=lambda _: pick_recovery_dialog.pick_files(
                                allow_multiple=False
                            ),
                        ),
                        selected_recovery,
                    ]
                ),
                confirm_button("Done?"),
            ],
            index=1,
        ),
    ]

    page.views.append(views[0])
    page.banner.open = True
    page.update()


flet.app(target=main, assets_dir="assets")
