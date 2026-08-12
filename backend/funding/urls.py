from rest_framework.routers import DefaultRouter

from .views import (
    BudgetLineViewSet,
    ExpenseViewSet,
    GrantProjectViewSet,
    GrantViewSet,
    InstallmentViewSet,
    ReportDeadlineViewSet,
)

router = DefaultRouter()
router.register("financements", GrantViewSet, basename="financement")
router.register("financements-projets", GrantProjectViewSet, basename="financement-projet")
router.register("lignes-budgetaires", BudgetLineViewSet, basename="ligne-budgetaire")
router.register("depenses", ExpenseViewSet, basename="depense")
router.register("echeances", ReportDeadlineViewSet, basename="echeance")
router.register("versements", InstallmentViewSet, basename="versement")

urlpatterns = router.urls