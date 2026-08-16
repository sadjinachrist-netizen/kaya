"""Serialiseurs du cadre logique et des indicateurs."""
from rest_framework import serializers

from .models import (
    Indicator,
    IndicatorDisaggregation,
    IndicatorReading,
    LogFrameElement,
)


class DisaggregationSerializer(serializers.ModelSerializer):
    dimension_label = serializers.CharField(source="get_dimension_display", read_only=True)

    class Meta:
        model = IndicatorDisaggregation
        fields = ["id", "indicator", "dimension", "dimension_label"]


class IndicatorReadingSerializer(serializers.ModelSerializer):
    indicator_code = serializers.CharField(source="indicator.code", read_only=True)
    taux_atteinte = serializers.FloatField(read_only=True)
    entered_by_name = serializers.CharField(source="entered_by.full_name", read_only=True)

    class Meta:
        model = IndicatorReading
        fields = ["id", "indicator", "indicator_code", "period_start", "period_end",
                  "achieved_value", "breakdown", "comment", "evidence", "status",
                  "taux_atteinte", "entered_by", "entered_by_name",
                  "validated_by", "created_at"]
        read_only_fields = ["status", "entered_by", "validated_by", "created_at"]

    def validate(self, attrs):
        debut = attrs.get("period_start") or getattr(self.instance, "period_start", None)
        fin = attrs.get("period_end") or getattr(self.instance, "period_end", None)
        if debut and fin and fin <= debut:
            raise serializers.ValidationError(
                {"period_end": "La fin de periode doit suivre le debut."}
            )
        return attrs


class IndicatorListSerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(source="element.project_id", read_only=True)
    project_code = serializers.CharField(source="element.project.code", read_only=True)
    element_code = serializers.CharField(source="element.code", read_only=True)
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)
    valeur_atteinte = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    taux_atteinte = serializers.FloatField(read_only=True)
    statut_atteinte = serializers.CharField(read_only=True)
    taux_attendu = serializers.FloatField(read_only=True)

    class Meta:
        model = Indicator
        fields = ["id", "code", "title", "unit", "unit_label", "baseline", "target",
                  "frequency", "computation_mode", "project", "project_code",
                  "element", "element_code",
                  "valeur_atteinte", "taux_atteinte", "statut_atteinte", "taux_attendu"]


class IndicatorDetailSerializer(IndicatorListSerializer):
    disaggregations = DisaggregationSerializer(many=True, read_only=True)
    readings = IndicatorReadingSerializer(many=True, read_only=True)
    valeur_calculee = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta(IndicatorListSerializer.Meta):
        fields = IndicatorListSerializer.Meta.fields + [
            "definition", "verification_source", "computation_source",
            "owner", "owner_name", "disaggregations", "readings", "valeur_calculee",
        ]

    def get_valeur_calculee(self, obj):
        valeur = obj.calculer()
        return None if valeur is None else str(valeur)


class LogFrameElementSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    nb_indicateurs = serializers.IntegerField(source="indicators.count", read_only=True)
    nb_enfants = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = LogFrameElement
        fields = ["id", "project", "type", "type_label", "code", "title",
                  "parent", "position", "nb_indicateurs", "nb_enfants"]

    def validate(self, attrs):
        element = LogFrameElement(**{**attrs})
        if self.instance:
            element.pk = self.instance.pk
        try:
            element.clean()
        except Exception as erreur:
            raise serializers.ValidationError(getattr(erreur, "message_dict", str(erreur)))
        return attrs


class LogFrameArbreSerializer(LogFrameElementSerializer):
    """Version arborescente, pour l'affichage du cadre logique complet."""

    indicators = IndicatorListSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()

    class Meta(LogFrameElementSerializer.Meta):
        fields = LogFrameElementSerializer.Meta.fields + ["indicators", "children"]

    def get_children(self, obj):
        return LogFrameArbreSerializer(obj.children.all(), many=True).data