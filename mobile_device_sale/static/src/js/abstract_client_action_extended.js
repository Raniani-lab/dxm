odoo.define('mobile_device_sale.ClientActionExtended', function (require) {
    'use strict';
    var ClientAction = require('stock_barcode.ClientAction')
    var LinesWidget = require('stock_barcode.LinesWidget');
    var core = require('web.core');
    var _t = core._t;
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
                // var btn_cnt = self.$('#scan_count');
                // btn_cnt.text(self.initialScanned)
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
                self.initialScanned = res.total_scanned;
            });

        },

        /**
         * Get media elements for play events sounds
         * @param
         * @return Audio Object
         * **/
        _getMedia: function(){
            this.error_sound = new Audio('/mobile_device_sale/static/src/sound/error.wav');
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
         _step_lot: function (barcode, linesActions) {
        if (! this.groups.group_production_lot) {
            self.error_sound.play();
            return Promise.reject();
        }
        this.currentStep = 'lot';
        var errorMessage;
        var self = this;

        // Bypass this step if needed.
        if (this.productsByBarcode[barcode]) {
            return this._step_product(barcode, linesActions);
        } else if (this.locationsByBarcode[barcode]) {
            return this._step_destination(barcode, linesActions);
        }

        var getProductFromLastScannedLine = function () {
            if (self.scannedLines.length) {
                var idOrVirtualId = self.scannedLines[self.scannedLines.length - 1];
                var line = _.find(self._getLines(self.currentState), function (line) {
                    return line.virtual_id === idOrVirtualId || line.id === idOrVirtualId;
                });
                if (line) {
                    var product = self.productsByBarcode[line.product_barcode];
                    // Product was added by lot or package
                    if (!product) {
                        return false;
                    }
                    product.barcode = line.product_barcode;
                    return product;
                }
            }
            return false;
        };

        var getProductFromCurrentPage = function () {
            return _.map(self.pages[self.currentPageIndex].lines, function (line) {
                return line.product_id.id;
            });
        };

        var getProductFromOperation = function () {
            return _.map(self._getLines(self.currentState), function (line) {
                return line.product_id.id;
            });
        };

        var readProduct = function (product_id) {
            var product_barcode = _.findKey(self.productsByBarcode, function (product) {
                return product.id === product_id;
            });

            if (product_barcode) {
                var product = self.productsByBarcode[product_barcode];
                product.barcode = product_barcode;
                return Promise.resolve(product);
            } else {
                return self._rpc({
                    model: 'product.product',
                    method: 'read',
                    args: [product_id],
                }).then(function (product) {
                    return Promise.resolve(product[0]);
                });
            }
        };

        var getLotInfo = function (lots) {
            var products_in_lots = _.map(lots, function (lot) {
                return lot.product_id[0];
            });
            var products = getProductFromLastScannedLine();
            var product_id = _.intersection(products, products_in_lots);
            if (! product_id.length) {
                products = getProductFromCurrentPage();
                product_id = _.intersection(products, products_in_lots);
            }
            if (! product_id.length) {
                products = getProductFromOperation();
                product_id = _.intersection(products, products_in_lots);
            }
            if (! product_id.length) {
                product_id = [lots[0].product_id[0]];
            }
            return readProduct(product_id[0]).then(function (product) {
                var lot = _.find(lots, function (lot) {
                    return lot.product_id[0] === product.id;
                });
                return Promise.resolve({lot_id: lot.id, lot_name: lot.display_name, product: product});
            });
        };

        var searchRead = function (barcode) {
            // Check before if it exists reservation with the lot.
            var line_with_lot = _.find(self.currentState.move_line_ids, function (line) {
                return (line.lot_id && line.lot_id[1] === barcode) || line.lot_name === barcode;
            });
            var def;
            if (line_with_lot) {
                def = Promise.resolve([{
                    name: barcode,
                    display_name: barcode,
                    id: line_with_lot.lot_id[0],
                    product_id: [line_with_lot.product_id.id, line_with_lot.display_name],
                }]);
            } else {
                def = self._rpc({
                    model: 'stock.production.lot',
                    method: 'search_read',
                    domain: [['name', '=', barcode]],
                });
            }
            return def.then(function (res) {
                if (! res.length) {
                    errorMessage = _t('The scanned lot does not match an existing one.');
                    self.error_sound.play();
                    return Promise.reject(errorMessage);
                }
                return getLotInfo(res);
            });
        };

        var create = function (barcode, product) {
            return self._rpc({
                model: 'stock.production.lot',
                method: 'create',
                args: [{
                    'name': barcode,
                    'product_id': product.id,
                    'company_id': self.currentState.company_id[0],
                }],
            });
        };

        var def;
        if (this.currentState.use_create_lots &&
            ! this.currentState.use_existing_lots) {
            // Do not create lot if product is not set. It could happens by a
            // direct lot scan from product or source location step.
            var product = getProductFromLastScannedLine();
            if (! product  || product.tracking === "none") {
                self.error_sound.play();
                return Promise.reject();
            }
            def = Promise.resolve({lot_name: barcode, product: product});
        } else if (! this.currentState.use_create_lots &&
                    this.currentState.use_existing_lots) {
            def = searchRead(barcode);
        } else {
            def = searchRead(barcode).then(function (res) {
                return Promise.resolve(res);
            }, function (errorMessage) {
                var product = getProductFromLastScannedLine();
                if (product && product.tracking !== "none") {
                    return create(barcode, product).then(function (lot_id) {
                        return Promise.resolve({lot_id: lot_id, lot_name: barcode, product: product});
                    });
                }
                self.error_sound.play();
                return Promise.reject(errorMessage);
            });
        }
        return def.then(function (lot_info) {
            var product = lot_info.product;
            if (product.tracking === 'serial' && self._lot_name_used(product, barcode)){
                errorMessage = _t('The scanned serial number is already used.');
                self.error_sound.play();
                return Promise.reject(errorMessage);
            }
            var res = self._incrementLines({
                'product': product,
                'barcode': lot_info.product.barcode,
                'lot_id': lot_info.lot_id,
                'lot_name': lot_info.lot_name
            });
            if (res.isNewLine) {
                self.scannedLines.push(res.lineDescription.virtual_id);
                linesActions.push([self.linesWidget.addProduct, [res.lineDescription, self.actionParams.model]]);
            } else {
                if (typeof res.has_error != "undefined"){
                    if (res.has_error){
                        self.error_sound.play();
                        errorMessage = _t(res.message);
                        return Promise.reject(res.message);
                    }

                }
                if (self.scannedLines.indexOf(res.lineDescription.id) === -1) {
                    self.scannedLines.push(res.lineDescription.id);
                }
                linesActions.push([self.linesWidget.incrementProduct, [res.id || res.virtualId, 1, self.actionParams.model]]);
                linesActions.push([self.linesWidget.setLotName, [res.id || res.virtualId, barcode]]);
            }
            return Promise.resolve({linesActions: linesActions});
        });
    },
        _step_product: function (barcode, linesActions) {
        var self = this;
        this.currentStep = 'product';
        var errorMessage;

        var product = this._isProduct(barcode);
        if (product) {
            if (product.tracking !== 'none') {
                this.currentStep = 'lot';
            }
            var res = this._incrementLines({'product': product, 'barcode': barcode});
            if (res.isNewLine) {
                if (this.actionParams.model === 'stock.inventory') {
                    // FIXME sle: add owner_id, prod_lot_id, owner_id, product_uom_id
                    return this._rpc({
                        model: 'product.product',
                        method: 'get_theoretical_quantity',
                        args: [
                            res.lineDescription.product_id.id,
                            res.lineDescription.location_id.id,
                        ],
                    }).then(function (theoretical_qty) {
                        res.lineDescription.theoretical_qty = theoretical_qty;
                        linesActions.push([self.linesWidget.addProduct, [res.lineDescription, self.actionParams.model]]);
                        self.scannedLines.push(res.id || res.virtualId);
                        return Promise.resolve({linesActions: linesActions});
                    });
                } else {
                    linesActions.push([this.linesWidget.addProduct, [res.lineDescription, this.actionParams.model]]);
                }
            } else {
                if (product.tracking === 'none') {
                    linesActions.push([this.linesWidget.incrementProduct, [res.id || res.virtualId, product.qty || 1, this.actionParams.model]]);
                } else {
                    linesActions.push([this.linesWidget.incrementProduct, [res.id || res.virtualId, 0, this.actionParams.model]]);
                }
            }
            this.scannedLines.push(res.id || res.virtualId);
            return Promise.resolve({linesActions: linesActions});
        } else {
            var success = function (res) {
                return Promise.resolve({linesActions: res.linesActions});
            };
            var fail = function (specializedErrorMessage) {
                self.currentStep = 'product';
                if (specializedErrorMessage){
                    self.error_sound.play();
                    return Promise.reject(specializedErrorMessage);
                }
                if (! self.scannedLines.length) {
                    if (self.groups.group_tracking_lot) {
                        errorMessage = _t("You are expected to scan one or more products or a package available at the picking's location");
                    } else {
                        errorMessage = _t('You are expected to scan one or more products.');
                    }
                    self.error_sound.play();
                    return Promise.reject(errorMessage);
                }

                var destinationLocation = self.locationsByBarcode[barcode];
                if (destinationLocation) {
                    return self._step_destination(barcode, linesActions);
                } else {
                    errorMessage = _t('You are expected to scan more products or a destination location.');
                    self.error_sound.play();
                    return Promise.reject(errorMessage);
                }
            };
            return self._step_lot(barcode, linesActions).then(success, function () {
                return self._step_package(barcode, linesActions).then(success, fail);
            });
        }
    },
        _incrementLines: function (params) {
            var self = this;
            var line = this._findCandidateLineToIncrement(params);
            var isNewLine = false;
            var response
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
                        if (this._change_scanned_products(params.product) || this.currentState.picking_type_code =='internal'){
                            console.log("ALL OK")
                        } else {
                            console.log("MAX NUMBER OF BARCODE REACHED")
                            response = {'has_error':true,'message':'MAX NUMBER OF BARCODE REACHED'}
                            return response
                        }
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
                    if (self.PermittedLotBarcodes.length){
                        var permitted_lot = _.find(self.PermittedLotBarcodes, function (lot) {
                        console.log('LOT')
                        console.log(lot)
                        return lot === params.lot_id
                         })
                    }else {
                        var permitted_lot = true
                    }


                    console.log("PERMITTED LOG.....")
                    console.log(permitted_lot)
                    if (permitted_lot){
                        console.log("PERMITTED LOT")
                        // Update scanned count
                        // console.log(this.scannedCount)
                        if (this._change_scanned_products(params.product) || this.currentState.picking_type_code =='internal'){
                            console.log("ALL OK")
                        } else {
                            console.log("MAX NUMBER OF BARCODE REACHED")

                            response = {'has_error':true,'message':'MAX NUMBER OF BARCODE REACHED'}
                            return response
                        }

                        //console.log(LinesWidget)
                        //this._reloadLineWidget(this.currentPageIndex);
                    } else {
                        console.log("LOT NOT PERMITTED")
                        response = {'has_error':true,'message':'Lot not match specs'}
                        return response
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