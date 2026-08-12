"""Serialiseurs des beneficiaires, avec pseudonymisation des champs nominatifs."""
from rest_framework import serializers

from .models import (
    Consent,
    DuplicateCandidate,
    Household,
    HouseholdProject,
    Person,
    Vulnerability,
)
from .services import enregistrer_menage

from projects.models import Project


class ProtectionNominative:
    """Masque les champs nominatifs pour les roles non habilites."""

    def peut_voir_nominatif(self):
        requete = self.context.get("request")
        if requete is None:
            return False
        return requete.user.has_permission("beneficiaire.voir_donnees_nominatives")


class VulnerabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerability
        fields = ["id", "code", "label", "weight"]


class PersonSerializer(ProtectionNominative, serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "first_name", "last_name", "sex", "birth_date",
                  "estimated_age", "age", "relation_to_head", "is_head",
                  "is_enrolled", "has_disability"]

    def get_first_name(self, obj):
        return obj.first_name if self.peut_voir_nominatif() else "—"

    def get_last_name(self, obj):
        return obj.last_name if self.peut_voir_nominatif() else "—"


class ConsentSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Consent
        fields = ["granted", "collection_mode", "collected_at", "withdrawn_at", "is_valid"]


class HouseholdListSerializer(ProtectionNominative, serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    nb_membres = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Household
        fields = ["id", "code", "head_name", "size", "nb_membres", "zone", "zone_name",
                  "residence_status", "validation_status", "registered_at"]

    def get_head_name(self, obj):
        """Champ nominatif : remplace par le code pour les roles non habilites."""
        return obj.head_name if self.peut_voir_nominatif() else obj.code


class HouseholdDetailSerializer(HouseholdListSerializer):
    members = PersonSerializer(many=True, read_only=True)
    consent = ConsentSerializer(read_only=True)
    vulnerabilities = VulnerabilitySerializer(many=True, read_only=True)
    vulnerability_score = serializers.IntegerField(read_only=True)
    sadd = serializers.DictField(read_only=True)
    zone_path = serializers.CharField(source="zone.full_path", read_only=True)
    registered_by_name = serializers.CharField(source="registered_by.full_name", read_only=True)

    class Meta(HouseholdListSerializer.Meta):
        fields = HouseholdListSerializer.Meta.fields + [
            "zone_path", "latitude", "longitude", "gps_accuracy",
            "members", "consent", "vulnerabilities", "vulnerability_score",
            "sadd", "registered_by", "registered_by_name", "client_uuid",
        ]


class PersonEntreeSerializer(serializers.ModelSerializer):
    """Membre transmis a la creation d'un menage."""

    class Meta:
        model = Person
        fields = ["first_name", "last_name", "sex", "birth_date", "estimated_age",
                  "relation_to_head", "is_head", "is_enrolled", "has_disability"]


class ConsentEntreeSerializer(serializers.Serializer):
    granted = serializers.BooleanField()
    collection_mode = serializers.ChoiceField(choices=Consent.Mode.choices)
    collected_at = serializers.DateTimeField(required=False)


class HouseholdCreateSerializer(serializers.ModelSerializer):
    members = PersonEntreeSerializer(many=True, write_only=True)
    consent = ConsentEntreeSerializer(write_only=True)
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Household
        fields = ["head_name", "size", "zone", "latitude", "longitude", "gps_accuracy",
                  "residence_status", "vulnerabilities", "client_uuid",
                  "members", "consent", "project"]

    

    def validate_members(self, valeur):
        if not valeur:
            raise serializers.ValidationError("Un menage comporte au moins un membre.")
        if sum(1 for m in valeur if m.get("is_head")) != 1:
            raise serializers.ValidationError(
                "Le menage doit designer exactement un chef de menage."
            )
        return valeur

    def validate_consent(self, valeur):
        if not valeur.get("granted"):
            raise serializers.ValidationError(
                "Sans consentement du beneficiaire, l'enregistrement est refuse."
            )
        return valeur

    def create(self, donnees_validees):
        membres = donnees_validees.pop("members")
        consentement = donnees_validees.pop("consent")
        projet = donnees_validees.pop("project", None)
        menage, doublons = enregistrer_menage(
            agent=self.context["request"].user,
            donnees=donnees_validees,
            membres=membres,
            consentement=consentement,
            projet=projet,
        )
        self._doublons = doublons
        return menage


class DuplicateCandidateSerializer(ProtectionNominative, serializers.ModelSerializer):
    menage_a = serializers.SerializerMethodField()
    menage_b = serializers.SerializerMethodField()

    class Meta:
        model = DuplicateCandidate
        fields = ["id", "menage_a", "menage_b", "score", "status",
                  "reviewed_by", "reviewed_at"]

    def _resume(self, menage):
        return {
            "id": menage.id,
            "code": menage.code,
            "head_name": menage.head_name if self.peut_voir_nominatif() else menage.code,
            "size": menage.size,
            "zone": menage.zone.name,
            "registered_at": menage.registered_at,
            "registered_by": menage.registered_by.username,
        }

    def get_menage_a(self, obj):
        return self._resume(obj.household_a)

    def get_menage_b(self, obj):
        return self._resume(obj.household_b)