"""Serialiseurs des activites."""
from rest_framework import serializers

from .models import Activity, ActivityParticipation, Attachment
from .services import generer_code


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "file", "mime_type", "size", "caption", "uploaded_at"]
        read_only_fields = ["mime_type", "size", "uploaded_at"]


class ParticipationSerializer(serializers.ModelSerializer):
    household_code = serializers.CharField(source="household.code", read_only=True)

    class Meta:
        model = ActivityParticipation
        fields = ["id", "household", "household_code", "males_count",
                  "females_count", "age_breakdown"]


class ActivityListSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    agent_name = serializers.CharField(source="agent.full_name", read_only=True)
    nb_alertes = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ["id", "code", "project", "project_code", "type", "type_label",
                  "activity_date", "zone", "zone_name", "status", "status_label",
                  "agent", "agent_name", "nb_alertes", "created_at"]

    def get_nb_alertes(self, obj):
        return len(obj.alertes_qualite)


class ActivityDetailSerializer(ActivityListSerializer):
    attachments = AttachmentSerializer(many=True, read_only=True)
    participations = ParticipationSerializer(many=True, read_only=True)
    alertes_qualite = serializers.ListField(read_only=True)
    participants_totaux = serializers.DictField(read_only=True)
    transitions_possibles = serializers.ListField(read_only=True)
    est_modifiable = serializers.BooleanField(read_only=True)
    validated_by_name = serializers.CharField(source="validated_by.full_name", read_only=True)

    class Meta(ActivityListSerializer.Meta):
        fields = ActivityListSerializer.Meta.fields + [
            "description", "results", "latitude", "longitude", "gps_accuracy",
            "attachments", "participations", "alertes_qualite", "participants_totaux",
            "transitions_possibles", "est_modifiable", "submitted_at",
            "validated_by", "validated_by_name", "validated_at", "rejection_reason",
            "entry_duration_seconds", "client_uuid",
        ]


class ActivityWriteSerializer(serializers.ModelSerializer):
    participations = ParticipationSerializer(many=True, required=False)

    class Meta:
        model = Activity
        fields = ["project", "type", "activity_date", "zone", "description", "results",
                  "latitude", "longitude", "gps_accuracy", "entry_duration_seconds",
                  "client_uuid", "participations"]

    def validate_project(self, projet):
        """Un agent ne peut saisir que sur un projet auquel il a acces."""
        from authorization.scopes import projets_accessibles

        utilisateur = self.context["request"].user
        if not projets_accessibles(utilisateur).filter(pk=projet.pk).exists():
            raise serializers.ValidationError(
                "Vous n'etes pas affecte a ce projet."
            )
        return projet

    def create(self, donnees):
        participations = donnees.pop("participations", [])
        activite = Activity.objects.create(
            code=generer_code(),
            agent=self.context["request"].user,
            **donnees,
        )
        for participation in participations:
            ActivityParticipation.objects.create(activity=activite, **participation)
        return activite

    def update(self, instance, donnees):
        donnees.pop("participations", None)
        return super().update(instance, donnees)


class RejetSerializer(serializers.Serializer):
    motif = serializers.CharField(max_length=1000)