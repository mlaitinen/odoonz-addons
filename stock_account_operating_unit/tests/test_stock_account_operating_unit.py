# © 2019 Eficent Business and IT Consulting Services S.L.
# - Jordi Ballester Alomar
# © 2019 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# Rujia Liu
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.stock.tests.common import TestStockCommon


class TestStockAccountOperatingUnit(TestStockCommon):
    def setUp(self):
        super(TestStockAccountOperatingUnit, self).setUp()
        self.res_groups = self.env["res.groups"]
        self.res_users_model = self.env["res.users"]
        self.aml_model = self.env["account.move.line"]
        self.account_model = self.env["account.account"]
        self.product_model = self.env["product.product"]
        self.product_cteg_model = self.env["product.category"]
        self.acc_type_model = self.env["account.account.type"]
        self.operating_unit_model = self.env["operating.unit"]
        self.company_model = self.env["res.company"]
        self.move_model = self.env["stock.move"]
        self.picking_model = self.env["stock.picking"]

        # Company
        self.company = self.env.ref("base.main_company")
        self.group_stock_manager = self.env.ref("stock.group_stock_manager")
        self.grp_acc_user = self.env.ref("account.group_account_invoice")
        self.grp_stock_user = self.env.ref("stock.group_stock_user")
        # Main Operating Unit
        self.ou1 = self.env.ref("operating_unit.main_operating_unit")
        # B2B Operating Unit
        self.b2b = self.env.ref("operating_unit.b2b_operating_unit")
        # B2C Operating Unit
        self.b2c = self.env.ref("operating_unit.b2c_operating_unit")
        # Partner
        self.partner1 = self.env.ref("base.res_partner_1")
        self.stock_location_stock = self.env.ref("stock.stock_location_stock")
        self.supplier_location = self.env.ref("stock.stock_location_suppliers")
        self.customer_location = self.env.ref("stock.stock_location_customers")

        # Create user1
        self.user1 = self._create_user(
            "stock_account_user_1",
            [self.grp_stock_user, self.grp_acc_user, self.group_stock_manager],
            self.company,
            [self.ou1, self.b2c],
        )
        # Create user2
        self.user2 = self._create_user(
            "stock_account_user_2",
            [self.grp_stock_user, self.grp_acc_user, self.group_stock_manager],
            self.company,
            [self.b2c],
        )
        # Create account for Goods Received Not Invoiced
        name = "Goods Received Not Invoiced"
        code = "grni"
        acc_type = self.env.ref("account.data_account_type_equity")
        self.account_grni = self._create_account(acc_type, name, code, self.company)
        # Create account for Cost of Goods Sold
        name = "Cost of Goods Sold"
        code = "cogs"
        acc_type = self.env.ref("account.data_account_type_expenses")
        self.account_cogs_id = self._create_account(acc_type, name, code, self.company)
        # Create account for Inventory
        name = "Inventory"
        code = "inventory"
        acc_type = self.env.ref("account.data_account_type_fixed_assets")
        self.account_inventory = self._create_account(
            acc_type, name, code, self.company
        )
        # Create account for Inter-OU Clearing
        name = "Inter-OU Clearing"
        code = "inter_ou"
        acc_type = self.env.ref("account.data_account_type_equity")
        self.account_inter_ou_clearing = self._create_account(
            acc_type, name, code, self.company
        )
        # Update company data
        self.company.write(
            {
                "inter_ou_clearing_account_id": self.account_inter_ou_clearing.id,
                "ou_is_self_balanced": True,
            }
        )

        # Create Product
        self.product = self._create_product()
        # Create incoming stock picking type
        self.incoming_id = self.env.ref("stock.warehouse0").in_type_id
        # Create incoming and internal stock picking types
        b2c_wh = self.env.ref("stock_operating_unit.stock_warehouse_b2c")
        b2c_wh.lot_stock_id.write({"operating_unit_id": self.b2c.id})
        self.location_b2c_id = b2c_wh.lot_stock_id
        self.b2c_type_in_id = b2c_wh.in_type_id
        self.b2c_type_int_id = b2c_wh.int_type_id
        self.b2c_type_out_id = b2c_wh.out_type_id

    def _create_user(self, login, groups, company, operating_units):
        """Create a user."""
        group_ids = [group.id for group in groups]
        user = self.res_users_model.create(
            {
                "name": "Test Stock Account User",
                "login": login,
                "password": "demo",
                "email": "example@yourcompany.com",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "operating_unit_ids": [(4, ou.id) for ou in operating_units],
                "groups_id": [(6, 0, group_ids)],
            }
        )
        return user

    def _create_account(self, acc_type, name, code, company):
        """Create an account."""
        account = self.account_model.create(
            {
                "name": name,
                "code": code,
                "user_type_id": acc_type.id,
                "company_id": company.id,
            }
        )
        return account

    def _create_product(self):
        """Create a Product with inventory valuation set to auto."""
        product_cteg = self.product_cteg_model.create(
            {
                "name": "test_product_ctg",
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": self.account_inventory.id,
                "property_stock_account_input_categ_id": self.account_grni.id,
                "property_stock_account_output_categ_id": self.account_cogs_id,
            }
        )
        product = self.product_model.create(
            {
                "name": "test_product",
                "categ_id": product_cteg.id,
                "type": "product",
                "list_price": 1.0,
                "standard_price": 1.0,
            }
        )
        return product

    def _create_picking(self, user, ou_id, picking_type, src_loc_id, dest_loc_id):
        """Create a Picking."""
        picking = self.picking_model.with_user(user.id).create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src_loc_id.id,
                "location_dest_id": dest_loc_id.id,
                "operating_unit_id": ou_id.id,
            }
        )
        self.move_model.with_user(user.id).create(
            {
                "name": "a move",
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": 1,
                "picking_id": picking.id,
                "location_id": src_loc_id.id,
                "location_dest_id": dest_loc_id.id,
            }
        )
        return picking

    def _confirm_receive(self, user_id, picking):
        """
        Checks the stock availability, validates and process the stock picking.
        """
        picking.action_confirm()
        picking.action_assign()
        res = picking.with_user(user_id).button_validate()
        wiz = Form(
            self.env["stock.immediate.transfer"].with_context(res["context"])
        ).save()
        wiz.process()

    def _check_account_balance(
        self, account_id, operating_unit=None, expected_balance=0.0
    ):
        """
        Check the balance of the account based on different operating units.
        """
        domain = [("account_id", "=", account_id)]
        if operating_unit:
            domain.extend([("operating_unit_id", "=", operating_unit.id)])

        balance = self._get_balance(domain)
        if operating_unit:
            self.assertEqual(
                balance,
                expected_balance,
                "Balance is not %s for Operating Unit %s."
                % (str(expected_balance), operating_unit.name),
            )
        else:
            self.assertEqual(
                balance,
                expected_balance,
                "Balance is not %s for all Operating Units." % str(expected_balance),
            )

    def _get_balance(self, domain):
        """
        Call read_group method and return the balance of particular account.
        """
        aml_rec = self.aml_model.read_group(
            domain, ["debit", "credit", "account_id"], ["account_id"]
        )
        if aml_rec:
            return aml_rec[0].get("debit", 0.0) - aml_rec[0].get("credit", 0.0)
        else:
            return 0.0

    def _check_ou_in_svl(self, picking_id, ou=None):
        scraps = self.env["stock.scrap"].search([("picking_id", "=", picking_id.id)])
        domain = [("product_id.type", "=", "product")]
        if scraps:
            domain.append(
                (
                    "id",
                    "in",
                    (
                        picking_id.move_lines + scraps.move_id
                    ).stock_valuation_layer_ids.ids,
                )
            )
        else:
            domain.append(
                ("id", "in", picking_id.move_lines.stock_valuation_layer_ids.ids)
            )
        svls = self.env["stock.valuation.layer"].search(domain)
        for svl in svls:
            if ou:
                self.assertEqual(svl.operating_unit_id, ou)

    def test_stock_operating_unit(self):
        with self.assertRaises(UserError):
            self.stock_location_stock.operating_unit_id = False
        with self.assertRaises(UserError):
            self.stock_location_stock.usage = "internal"
            self.stock_location_stock.operating_unit_id = False

    def test_pickings(self):
        """Test account balances during receiving stock into the main
        operating unit, then into b2c operating unit, and then transfer stock
        from main ou to b2c."""
        # Create Incoming Shipment 1
        self.picking = self._create_picking(
            self.user1,
            self.ou1,
            self.incoming_id,
            self.supplier_location,
            self.stock_location_stock,
        )
        # Receive it
        self._confirm_receive(self.user1.id, self.picking)
        # check destination ou is ou1
        # self._check_ou_in_svl(self.picking, ou=self.ou1)
        # GL account ‘Inventory’ has balance 1 irrespective of the OU
        expected_balance = 1.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=None,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 1 on OU main_operating_unit
        expected_balance = 1.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.ou1,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 0 on OU B2C
        expected_balance = 0.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.b2c,
            expected_balance=expected_balance,
        )
        # GL account ‘Goods Received Not Invoiced’ has balance - 1
        # irrespective of the OU
        expected_balance = -1.0
        self._check_account_balance(
            self.account_grni.id, operating_unit=None, expected_balance=expected_balance
        )
        # GL account ‘Goods Received Not Invoiced’ has balance -1 on Main OU
        expected_balance = -1.0
        self._check_account_balance(
            self.account_grni.id,
            operating_unit=self.ou1,
            expected_balance=expected_balance,
        )
        # GL account ‘Goods Received Not Invoiced’ has balance 0 on OU b2c
        expected_balance = 0.0
        self._check_account_balance(
            self.account_grni.id,
            operating_unit=self.b2c,
            expected_balance=expected_balance,
        )

        # Create Incoming Shipment 2
        self.picking = self._create_picking(
            self.user2,
            self.b2c,
            self.b2c_type_in_id,
            self.supplier_location,
            self.location_b2c_id,
        )

        # Receive it
        self._confirm_receive(self.user2.id, self.picking)
        # check destination ou is b2c
        # self._check_ou_in_svl(self.picking, ou=self.b2c)
        # GL account ‘Inventory’ has balance 2 irrespective of the OU
        expected_balance = 2.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=None,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 1 on OU main_operating_unit
        expected_balance = 1.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.ou1,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 1 on OU b2c
        expected_balance = 1.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.b2c,
            expected_balance=expected_balance,
        )
        # GL account ‘Goods Received Not Invoiced’ has balance - 2
        # irrespective of the OU
        expected_balance = -2.0
        self._check_account_balance(
            self.account_grni.id, operating_unit=None, expected_balance=expected_balance
        )
        # GL account ‘Goods Received Not Invoiced’ has balance -1 on Main OU
        expected_balance = -1.0
        self._check_account_balance(
            self.account_grni.id,
            operating_unit=self.ou1,
            expected_balance=expected_balance,
        )
        # GL account ‘Goods Received Not Invoiced’ has balance 0 on OU b2c
        expected_balance = -1.0
        self._check_account_balance(
            self.account_grni.id,
            operating_unit=self.b2c,
            expected_balance=expected_balance,
        )

        # Create Internal Transfer
        self.picking = self._create_picking(
            self.user1,
            self.b2c,
            self.b2c_type_int_id,
            self.stock_location_stock,
            self.location_b2c_id,
        )
        # Receive it
        self._confirm_receive(self.user1.id, self.picking)
        # GL account ‘Inventory’ has balance 2 irrespective of the OU
        expected_balance = 2.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=None,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 0 on OU main_operating_unit
        expected_balance = 0.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.ou1,
            expected_balance=expected_balance,
        )
        # GL account ‘Inventory’ has balance 2 on OU b2c
        expected_balance = 2.0
        self._check_account_balance(
            self.account_inventory.id,
            operating_unit=self.b2c,
            expected_balance=expected_balance,
        )
        # GL account ‘Inter-OU clearing’ has balance 0 irrespective of the OU
        expected_balance = 0.0
        self._check_account_balance(
            self.account_inter_ou_clearing.id,
            operating_unit=None,
            expected_balance=expected_balance,
        )

        # Create shippment from vendor to customer
        self.picking = self._create_picking(
            self.user1,
            self.ou1,
            self.incoming_id,
            self.supplier_location,
            self.customer_location,
        )
        # Receive it
        self._confirm_receive(self.user1.id, self.picking)
        account_move = self.env["account.move"].search(
            [("stock_move_id", "=", self.picking.move_lines[0].id)]
        )
        account_move.line_ids.mapped("operating_unit_id")
        # Confirm the ou is picking type's ou
        self.assertEqual(
            account_move.line_ids.mapped("operating_unit_id"),
            self.picking.picking_type_id.warehouse_id.operating_unit_id,
        )
        # check operating units on both svls are from picking_id.operating_unit_id
        self._check_ou_in_svl(self.picking, ou=self.picking.operating_unit_id)
        # Create outgoing shipment
        self.picking = self._create_picking(
            self.user1,
            self.b2c,
            self.b2c_type_out_id,
            self.location_b2c_id,
            self.customer_location,
        )
        # Receive it
        self._confirm_receive(self.user1.id, self.picking)
        # check source ou is b2c
        # self._check_ou_in_svl(self.picking, ou=self.b2c)
