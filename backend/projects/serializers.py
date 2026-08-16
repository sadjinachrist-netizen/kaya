"""Serialiseurs des projets."""
from rest_framework import serializers

from referentials.models import Sector, Zone

from .models import Amendment, InterventionSite, Project, TeamMember


class InterventionSiteSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    zone_path = serializers.CharField(source="zone.full_path", read_only=True)

    class Meta:
        model = InterventionSite
        fields = ["id", "zone", "zone_name", "zone_path", "latitude", "longitude", "target_population"]


class TeamMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    role_label = serializers.CharField(source="get_project_role_display", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "user", "user_name", "project_role", "role_label",
                  "start_date", "end_date", "is_active"]


class ProjectListSerializer(serializers.ModelSerializer):
    """Version allegee pour les listes."""

    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    sectors = serializers.SlugRelatedField(many=True, read_only=True, slug_field="label")

    class Meta:
        model = Project
        fields = ["id", "code", "title", "status", "status_label", "sectors",
                  "start_date", "end_date", "manager", "manager_name",
                  "target_beneficiaries", "progress_rate"]


class ProjectSerializer(serializers.ModelSerializer):
    """Version detaillee."""

    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    sector_labels = serializers.SlugRelatedField(
        source="sectors", many=True, read_only=True, slug_field="label"
    )
    sites = InterventionSiteSerializer(many=True, read_only=True)
    members = TeamMemberSerializer(many=True, read_only=True)
    transitions_possibles = serializers.ListField(read_only=True)
    avancement = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "code", "title", "description", "sectors", "sector_labels",
                  "start_date", "end_date", "status", "status_label",
                  "target_beneficiaries", "progress_rate", "avancement",
                  "manager", "manager_name", "sites", "members",
                  "transitions_possibles", "created_at", "updated_at"]
        read_only_fields = ["status", "progress_rate", "created_at", "updated_at"]

    def get_avancement(self, obj):
        return obj.calculer_avancement()

    def validate(self, attrs):
        debut = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        fin = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if debut and fin and fin <= debut:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit etre posterieure a la date de debut."}
            )
        return attrs


class ChangementStatutSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=Project.Status.choices)
    motif = serializers.CharField(required=False, allow_blank=True, max_length=255)