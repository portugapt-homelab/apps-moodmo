import csv
import json
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    FormView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from moods.forms import MoodForm, UploadFileForm, ExportOptionsForm
from moods.mixins import UserIsOwnerMixin, SetUserMixin
from moods.models import Mood


class MoodListView(LoginRequiredMixin, ListView):
    model = Mood
    template_name = "moods/mood_list.html"


class MoodCreateView(LoginRequiredMixin, SetUserMixin, CreateView):
    model = Mood
    form_class = MoodForm
    template_name = "moods/mood_create.html"
    success_url = reverse_lazy("mood_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MoodUpdateView(LoginRequiredMixin, UserIsOwnerMixin, SetUserMixin, UpdateView):
    model = Mood
    form_class = MoodForm
    template_name = "moods/mood_update.html"
    success_url = reverse_lazy("mood_list")


class MoodDeleteView(LoginRequiredMixin, UserIsOwnerMixin, DeleteView):
    model = Mood
    template_name = "moods/mood_delete.html"
    success_url = reverse_lazy("mood_list")
    context_object_name = "mood"


class MoodImportView(LoginRequiredMixin, FormView):
    form_class = UploadFileForm
    template_name = "moods/mood_import.html"
    success_url = reverse_lazy("mood_list")

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        file = form.cleaned_data["file"]

        # Check that file is a CSV or a JSON
        if not (file.name.endswith(".csv") or file.name.endswith(".json")):
            form.add_error("file", "Only CSV or JSON files are allowed.")
            return self.form_invalid(form)
        try:
            if file.name.endswith(".csv"):
                csv_data = file.read().decode("utf-8")
                csv_reader = csv.DictReader(csv_data.splitlines())
                moods = [
                    Mood(
                        user=self.request.user,
                        mood=row["mood"],
                        note_title=row["note_title"],
                        note=row["note"],
                        timestamp=row["timestamp"],
                    )
                    for row in csv_reader
                ]

                Mood.objects.bulk_create(moods)

            elif file.name.endswith(".json"):
                json_data = json.loads(file.read().decode("utf-8"))
                moods = [
                    Mood(
                        user=self.request.user,
                        mood=item["mood"],
                        note_title=item["note_title"],
                        note=item["note"],
                        timestamp=datetime.strptime(
                            item["timestamp"],
                            "%Y-%m-%d %H:%M:%S %z",
                        ),
                    )
                    for item in json_data
                ]

                Mood.objects.bulk_create(moods)

        except (csv.Error, json.JSONDecodeError) as e:
            form.add_error("file", f"Error reading file: {e}")
            return self.form_invalid(form)

        return super().form_valid(form)


class MoodExportView(LoginRequiredMixin, FormView):
    form_class = ExportOptionsForm
    template_name = "moods/mood_export.html"
    success_url = reverse_lazy("mood_list")

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            moods = Mood.objects.filter(user=self.request.user).order_by("-timestamp")
            export_format = form.cleaned_data["export_format"]
            current_date = datetime.now().strftime("%Y_%m_%d")

            if export_format == "json":
                data = [
                    {
                        "mood": mood.mood,
                        "note_title": mood.note_title,
                        "note": mood.note,
                        "timestamp": mood.timestamp.strftime("%Y-%m-%d %H:%M:%S %z"),
                    }
                    for mood in moods
                ]

                json_data = json.dumps(data, indent=2)
                response = HttpResponse(json_data, content_type="application/json")
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="moodmo_export_{current_date}.json"'

                return response
            else:
                response = HttpResponse(content_type="text/csv")
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="moodmo_export_{current_date}.csv"'

                writer = csv.writer(response)
                writer.writerow(["mood", "note_title", "note", "timestamp"])

                writer.writerows(
                    [
                        [
                            mood.mood,
                            mood.note_title,
                            mood.note,
                            mood.timestamp.strftime("%Y-%m-%d %H:%M:%S %z"),
                        ]
                        for mood in moods
                    ]
                )

                return response

        return self.form_invalid(form)
