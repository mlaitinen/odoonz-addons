# Copyright 2017 Graeme Gellatly
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductAttributeGroup(models.Model):

    _name = "product.attribute.group"
    _description = "Product Attribute Group"
    _order = "attribute_id, name asc"

    name = fields.Char(required=True)
    attribute_id = fields.Many2one(
        comodel_name="product.attribute",
        string="Product Attribute",
        ondelete="restrict",
        required=True,
    )
    value_ids = fields.Many2many(
        comodel_name="product.attribute.value", string="Product Attribute Values"
    )
    attribute_line_ids = fields.Many2many(
        comodel_name="product.template.attribute.line",
        string="Product Attributes",
        copy=False,
    )

    _sql_constraints = [
        ("uniq_name", "unique(name)", "The attribute group name must be unique")
    ]

    def write(self, vals):
        res = super().write(vals)
        if "value_ids" in vals:
            for attr_group in self:
                for attr_line in attr_group.attribute_line_ids:
                    attr_line.onchange_attr_group()
                    attr_line.product_tmpl_id.with_delay()._create_variant_ids()
        return res

    def copy(self, default=None):
        """
        Override copy to ensure the copy is distinguishable
        from original and is not assigned to any products.
        :param default:
        :return: newly created record
        """
        default = dict(default or {})
        default["name"] = "%s (Copy)" % self.name
        return super().copy(default=default)

    def button_copy(self):
        """
        Allows duplication of attribute groups from tree view
        :return: refreshed view of attribute groups
        """
        self.ensure_one()
        self.copy()
        return self.env["ir.actions.act_window"].for_xml_id(
            "product_attribute_group", "product_attribute_group_act_window"
        )
