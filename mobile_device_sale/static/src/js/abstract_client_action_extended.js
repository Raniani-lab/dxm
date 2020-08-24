odoo.define('mobile_device_sale.ClientActionExtended', function (require) {
    'use strict';
    var ClientAction = require('stock_barcode.ClientAction')
    var LinesWidget = require('stock_barcode.LinesWidget');

    var ClientActionExtended = ClientAction.include({


        willStart: function () {
            var self = this;
            this.scannedCount = 0;
            var recordId = this.actionParams.pickingId || this.actionParams.inventoryId;
            return Promise.all([
                self._super.apply(self, arguments),
                self._getState(recordId),
                self._getProductBarcodes(),
                self._getLocationBarcodes(),
                self._getPermittedLotBarcodes(this.actionParams.pickingId),
                self._getMedia()
            ]).then(function () {
                return self._loadNomenclature();
            });
        },

        /**
         * Actualize scanned number
         * **/
        _change_scanned_products: function(product){
            console.log("CHECKING PRODUCT QUANTITY SCANNED")
            var max_qty = this.ProductsQuantity[product.id]['quantity'];
            console.log("max_qty:")
            console.log(max_qty)
            console.log('scannedCount')
            console.log(this.scannedCount)
            if (this.scannedCount < max_qty){
                this.scannedCount += 1;
                var btn_cnt = this.$('#scan_count');
                btn_cnt.text(this.scannedCount)
                this.ProductsQuantity[product.id]['scanned_qty'] += 1
                return true
            } else {
                return false
            }

        },

        /**
         * Get permitted lot barcodes according to move line specs
         * @param {integer}[picking_id] Stock Picking ID
         * @return {array}
         * **/
        _getPermittedLotBarcodes: function(picking_id){
            var self = this;
            return this._rpc({
                'model': 'stock.picking',
                'method': 'get_similar_barcode',
                'args': [picking_id],
            }).then(function (res) {
                console.log(res);
                self.PermittedLotBarcodes = res.lots;
                self.ProductsQuantity = res.products_quants;
            });

        },

        /**
         * Get media elements for play events sounds
         * @param
         * @return Audio Object
         * **/
        _getMedia: function(){
            this.error_sound = new Audio('/mobile_device_sale/static/src/sound/error.mp3');
        },

        /**
         * Main method called when a quantity needs to be incremented or a lot set on a line.
         * it calls `this._findCandidateLineToIncrement` first, if nothing is found it may use
         * `this._makeNewLine`.
         *
         * @private
         * @param {Object} params information needed to find the potential candidate line
         * @param {Object} params.product
         * @param {Object} params.lot_id
         * @param {Object} params.lot_name
         * @param {Object} params.package_id
         * @param {Object} params.result_package_id
         * @param {Boolean} params.doNotClearLineHighlight don't clear the previous line highlight when
         *     highlighting a new one
         * @return {object} object wrapping the incremented line and some other informations
         */
        _incrementLines: function (params) {
            var self = this;
            var line = this._findCandidateLineToIncrement(params);
            var isNewLine = false;
            if (line) {
                // Update the line with the processed quantity.
                if (params.product.tracking === 'none' ||
                    params.lot_id ||
                    params.lot_name
                    ) {
                    if (this.actionParams.model === 'stock.picking') {
                        line.qty_done += params.product.qty || 1;
                        // Update scanned count
                        // console.log(this.scannedCount)
                        this._change_scanned_products(params.product);
                        if (params.package_id) {
                            line.package_id = params.package_id;
                        }
                        if (params.result_package_id) {
                            line.result_package_id = params.result_package_id;
                        }
                    } else if (this.actionParams.model === 'stock.inventory') {
                        line.product_qty += params.product.qty || 1;
                    }
                }
            } else {
                isNewLine = true;

                // Check if barcode pass lines specifications
                if (this.actionParams.model === 'stock.picking'){

                    var permitted_lot = _.find(self.PermittedLotBarcodes, function (lot) {
                        console.log('LOT')
                        console.log(lot)
                        return lot === params.lot_id
                    })
                    console.log("PERMITTED LOG.....")
                    console.log(permitted_lot)
                    if (permitted_lot){
                        console.log("PERMITTED LOT")
                        // Update scanned count
                        // console.log(this.scannedCount)
                        if (this._change_scanned_products(params.product)){
                            console.log("ALL OK")
                        } else {
                            console.log("MAX NUMBER OF BARCODE REACHED")
                            this.error_sound.play();
                            return Promise.reject("MAX NUMBER OF BARCODE REACHED")
                        }

                        //console.log(LinesWidget)
                        //this._reloadLineWidget(this.currentPageIndex);
                    } else {
                        console.log("LOT NOT PERMITTED")
                        this.error_sound.play();
                        return Promise.reject("Lot not match specs")
                    }

                }

                // Create a line with the processed quantity.
                if (params.product.tracking === 'none' ||
                    params.lot_id ||
                    params.lot_name
                    ) {
                    console.log("Creating line I.....")
                    line = this._makeNewLine(params.product, params.barcode, params.product.qty || 1, params.package_id, params.result_package_id);
                } else {
                    console.log("Creating line II.....")
                    line = this._makeNewLine(params.product, params.barcode, 0, params.package_id, params.result_package_id);
                }
                this._getLines(this.currentState).push(line);
                this.pages[this.currentPageIndex].lines.push(line);
            }
            if (this.actionParams.model === 'stock.picking') {
                if (params.lot_id) {
                    line.lot_id = [params.lot_id];
                }
                if (params.lot_name) {
                    line.lot_name = params.lot_name;
                }
            } else if (this.actionParams.model === 'stock.inventory') {
                if (params.lot_id) {
                    line.prod_lot_id = [params.lot_id, params.lot_name];
                }
            }
            return {
                'id': line.id,
                'virtualId': line.virtual_id,
                'lineDescription': line,
                'isNewLine': isNewLine,
            };
        },

    })

    return ClientActionExtended

});