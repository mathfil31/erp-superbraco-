
from django.db import models, transaction


class Produto(models.Model):
    codigo = models.CharField(
        max_length=50, unique=True,
        verbose_name="Código do produto"
    )
    nome = models.CharField(
        max_length=200, verbose_name="Nome do produto"
    )
    descricao = models.TextField(
        blank=True, verbose_name="Descrição"
    )
    categoria = models.CharField(
        max_length=100, blank=True,
        verbose_name="Categoria"
    )
    unidade = models.CharField(
        max_length=20, default="UN",
        verbose_name="Unidade de medida"
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Quantidade em estoque"
    )
    estoque_minimo = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Estoque mínimo"
    )
    custo_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Custo unitário"
    )
    foto = models.ImageField(
        upload_to="produtos/", blank=True, null=True,
        verbose_name="Foto do produto"
    )
    ativo = models.BooleanField(
        default=True, verbose_name="Produto ativo"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True, verbose_name="Data de cadastro"
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Compra(models.Model):
    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("RECEBIDA", "Recebida"),
        ("CANCELADA", "Cancelada"),
    ]

    numero = models.CharField(
        max_length=30, unique=True,
        verbose_name="Número do pedido / PO"
    )
    fornecedor = models.CharField(
        max_length=200, verbose_name="Fornecedor"
    )
    data_pedido = models.DateField(
        auto_now_add=True, verbose_name="Data do pedido"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default="PENDENTE", verbose_name="Status"
    )
    observacoes = models.TextField(
        blank=True, verbose_name="Observações"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"{self.numero} - {self.fornecedor}"

    @property
    def valor_total(self):
        return sum(
            (item.subtotal for item in self.itens.all()),
            start=0
        )

    @transaction.atomic
    def receber(self):
        if not self.pk:
            raise ValueError("Salve a compra antes de recebê-la.")

        compra = Compra.objects.select_for_update().get(pk=self.pk)

        if compra.status == "RECEBIDA":
            return False

        if compra.status == "CANCELADA":
            raise ValueError(
                "Não é possível receber uma compra cancelada."
            )

        itens = list(compra.itens.all())

        if not itens:
            raise ValueError(
                "Cadastre pelo menos um produto antes de receber."
            )

        for item in itens:
            produto = Produto.objects.select_for_update().get(
                pk=item.produto_id
            )

            saldo_anterior = produto.quantidade
            produto.quantidade += item.quantidade
            saldo_posterior = produto.quantidade
            produto.custo_unitario = item.custo_unitario

            produto.save(
                update_fields=["quantidade", "custo_unitario"]
            )

            MovimentacaoEstoque.objects.create(
                produto=produto,
                tipo="ENTRADA",
                quantidade=item.quantidade,
                saldo_anterior=saldo_anterior,
                saldo_posterior=saldo_posterior,
                compra=compra,
                observacao=f"Recebimento da compra {compra.numero}",
            )

        compra.status = "RECEBIDA"
        compra.save(update_fields=["status"])
        self.status = "RECEBIDA"
        return True


class ItemCompra(models.Model):
    compra = models.ForeignKey(
        Compra, on_delete=models.CASCADE,
        related_name="itens", verbose_name="Compra"
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT,
        verbose_name="Produto"
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Quantidade comprada"
    )
    custo_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Custo unitário"
    )

    class Meta:
        verbose_name = "Item da compra"
        verbose_name_plural = "Itens da compra"

    def __str__(self):
        return f"{self.produto} - {self.quantidade}"

    @property
    def subtotal(self):
        return self.quantidade * self.custo_unitario


class MovimentacaoEstoque(models.Model):
    TIPOS = [
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
        ("AJUSTE", "Ajuste"),
    ]

    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
        verbose_name="Produto",
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
        verbose_name="Tipo de movimentação",
    )
    quantidade = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantidade movimentada",
    )
    saldo_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Saldo anterior",
    )
    saldo_posterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Saldo posterior",
    )
    compra = models.ForeignKey(
        Compra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes",
        verbose_name="Compra relacionada",
    )
    observacao = models.TextField(
        blank=True, verbose_name="Observação"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True, verbose_name="Data da movimentação"
    )

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Movimentação de estoque"
        verbose_name_plural = "Movimentações de estoque"

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - "
            f"{self.produto.nome} - {self.quantidade}"
        )
  