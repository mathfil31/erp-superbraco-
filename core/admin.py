
from django.contrib import admin, messages
from .models import Produto, Compra, ItemCompra, MovimentacaoEstoque


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "categoria",
        "quantidade",
        "unidade",
        "custo_unitario",
        "ativo",
    )
    search_fields = ("codigo", "nome", "categoria")
    list_filter = ("categoria", "ativo")


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    fields = (
        "produto",
        "quantidade",
        "custo_unitario",
        "subtotal",
    )
    readonly_fields = ("subtotal",)

    @admin.display(description="Subtotal")
    def subtotal(self, obj):
        if obj.quantidade is None:
            return "—"
        return obj.quantidade * obj.custo_unitario


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "fornecedor",
        "data_pedido",
        "status",
        "valor_total_display",
    )
    search_fields = ("numero", "fornecedor")
    list_filter = ("status", "data_pedido")
    readonly_fields = ("data_pedido", "status")
    inlines = [ItemCompraInline]
    actions = ["receber_compras"]

    @admin.display(description="Valor total")
    def valor_total_display(self, obj):
        return obj.valor_total

    @admin.action(description="Receber materiais e atualizar estoque")
    def receber_compras(self, request, queryset):
        recebidas = 0
        ignoradas = 0
        erros = []

        for compra in queryset:
            try:
                resultado = compra.receber()
                if resultado:
                    recebidas += 1
                else:
                    ignoradas += 1
            except Exception as erro:
                erros.append(f"{compra.numero}: {erro}")

        if recebidas:
            self.message_user(
                request,
                f"{recebidas} compra(s) recebida(s). Estoque atualizado.",
                level=messages.SUCCESS,
            )

        if ignoradas:
            self.message_user(
                request,
                f"{ignoradas} compra(s) já estava(m) recebida(s).",
                level=messages.WARNING,
            )

        if erros:
            self.message_user(
                request,
                "Falha ao receber: " + "; ".join(erros),
                level=messages.ERROR,
            )


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "criado_em",
        "produto",
        "tipo",
        "quantidade",
        "saldo_anterior",
        "saldo_posterior",
        "compra",
    )
    list_filter = ("tipo", "criado_em")
    search_fields = (
        "produto__codigo",
        "produto__nome",
        "compra__numero",
        "observacao",
    )
    readonly_fields = (
        "produto",
        "tipo",
        "quantidade",
        "saldo_anterior",
        "saldo_posterior",
        "compra",
        "observacao",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
