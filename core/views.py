from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

from .models import Produto, Compra, MovimentacaoEstoque


def dashboard(request):
    produtos = Produto.objects.filter(ativo=True)
    compras = Compra.objects.all()

    valor_calculado = ExpressionWrapper(
        F("quantidade") * F("custo_unitario"),
        output_field=DecimalField(
            max_digits=20,
            decimal_places=2
        )
    )

    valor_estoque = produtos.aggregate(
        total=Sum(valor_calculado)
    )["total"] or Decimal("0.00")

    contexto = {
        "total_produtos": produtos.count(),

        "total_unidades": produtos.aggregate(
            total=Sum("quantidade")
        )["total"] or Decimal("0.00"),

        "produtos_baixo_estoque": produtos.filter(
            estoque_minimo__gt=0,
            quantidade__lte=F("estoque_minimo")
        ).count(),

        "valor_estoque": valor_estoque,

        "total_compras": compras.count(),

        "compras_pendentes": compras.filter(
            status="PENDENTE"
        ).count(),

        "compras_recentes": compras.order_by(
            "-criado_em"
        )[:5],

        "movimentacoes_recentes": (
            MovimentacaoEstoque.objects
            .select_related("produto", "compra")
            .order_by("-criado_em")[:5]
        ),
    }

    return render(
        request,
        "core/dashboard.html",
        contexto
    )