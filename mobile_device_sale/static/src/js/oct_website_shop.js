odoo.define('oct_website_sale.sale', function (require) {
    'use strict';
    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;

    $(document).ready(function () {
        console.log("DOCUMENT READY.....")
        var website_id = $("html").data('website-id') | 0;
        ajax.jsonRpc('/shop/get_mobile_device_sell_website', 'call', {}).then(function (data) {
            console.log(data);
            var website_for_sell = data.website_mobile_sell;

            if (website_for_sell === website_id) {

                console.log("WEBSITE TO SELL MOBILE DEVICES.....");
                /* Load products stock and price on grid */
                if ($('#products_grid').length > 0){

                    $(document).on('click', '#reset_specs_filter', function (ev) {
                        let url = window.location.href;
                        window.location.href = url.split('?')[0];
                    })


                    console.log("GETTING PRODUCT GRID DATA");
                    $(".oe_product ").each(function () {
                        var product_container = $(this);
                        var product_id = $(this).find("input[name='product_id']").val();
                        var specs = product_container.find('.specs_selected').data('specs');
                        var inventory_policy = product_container.find('.oct_stock_qty').data('inventory-policy');
                        var available_threshold = product_container.find('.oct_stock_qty').data('inventory-threshold');





                        // product_container.find(".o_wsale_product_btn").hide();
                        ajax.jsonRpc('/shop/get_product_info/grid', 'call', {
                            product_id: product_id,
                            specs: specs
                        }).then(function (data){

                            if (data) {
                                // console.log(data);
                                var specs_quant = data.specs_quant;
                                var specs_quant_container = product_container.find('.specs_quant');
                                var specs_paragraph = product_container.find('.specs_paragraph');
                                specs_quant_container.html(specs_quant);
                                // specs_paragraph.removeClass('oct_hidden');
                                // console.log(data.product_data);
                                for (var product_grade_id in data.product_data){
                                    // console.log(data.product_data[product_grade_id]);
                                    var price = data.product_data[product_grade_id][0];
                                    var stock = data.product_data[product_grade_id][1];
                                    var label_selector = 'label[data-grade-id="'+ product_grade_id + '"]';
                                    var grade_label = product_container.find(label_selector);
                                    var price_container = grade_label.find('.price');
                                    price_container.html(price);
                                    var stock_container = grade_label.find('.stock');


                                        if (inventory_policy === 'never'){

                                            grade_label.find('input').prop('disabled', false);
                                            grade_label.find('input').prop('max', 1000);

                                            if (stock > 0){
                                                stock_container.html(stock);
                                            } else {
                                                stock_container.html("On Demand");
                                            }

                                        } else if (inventory_policy === 'always') {

                                            if (stock > 0){
                                                stock_container.html(stock);
                                            } else {
                                                grade_label.find('input').prop('disabled', true);
                                                stock_container.html(stock);
                                                grade_label.addClass("oct_no_stock");
                                            }

                                        } else if (inventory_policy === 'threshold') {

                                            if (stock > available_threshold){

                                                stock_container.html("Available");

                                            } else if (stock <= available_threshold && stock !== 0) {

                                                grade_label.find('input').prop('disabled', false);
                                                stock_container.html(stock);

                                            } else if (stock === 0){

                                                grade_label.find('input').prop('disabled', true);
                                                stock_container.html(stock);
                                                grade_label.addClass("oct_no_stock");

                                            }

                                        }



                                }


                            } else {

                                var dialog = new Dialog(this, {
                                    size: 'medium',
                                    dialogClass: 'o_act_window',
                                    title: _t("Connection Error"),
                                    $content: $(_t("<span class='text-center' style='padding: 2rem;'>Error fetching products information. Please, try again later.</span>"))
                                });
                                dialog.open();

                            }

                        }); // END then function



                    }); // End each

                } else if ($("#product_detail").length > 0) {

                console.log("GETTING PRODUCT DETAIL DATA");
                var product_container = $("#product_detail");
                var product_id = product_container.find("input[name='product_id']").val();

                var inventory_policy = product_container.find('.oct_stock_qty').data('inventory-policy');

                var available_threshold = parseInt(product_container.find('.oct_stock_qty').
                    data('inventory-threshold'));

                console.log(inventory_policy)
                console.log(available_threshold)
                // product_container.find(".o_wsale_product_btn").hide();
                ajax.jsonRpc('/shop/get_product_info/detail', 'call', {
                product_id: product_id
                }).then(function(data) {
                    if (data) {
                        for (var product_grade_id in data.product_data){
                            // console.log(data.product_data[product_grade_id]);
                            var price = data.product_data[product_grade_id][0];
                            var stock = data.product_data[product_grade_id][1];
                            var label_selector = 'label[data-grade-id="'+ product_grade_id + '"]';
                            var grade_label = product_container.find(label_selector);
                            var price_container = grade_label.find('.price');
                            price_container.html(price);
                            var stock_container = grade_label.find('.stock');


                                if (inventory_policy === 'always') {

                                    stock_container.html(stock);
                                    if (stock === 0){
                                        grade_label.addClass("oct_no_stock");
                                        grade_label.find('input').prop('disabled', true);
                                    }

                                } else if (inventory_policy === 'threshold'){

                                    if (parseInt(stock) > available_threshold) {
                                        console.log("STOCK > AVAILABLE")
                                        stock_container.html("Available");
                                    }
                                    grade_label.find('input').prop('max', stock);
                                    if (stock === 0){
                                        grade_label.addClass("oct_no_stock");
                                        stock_container.html(stock);
                                    }
                                    if (stock < available_threshold  && stock !== 0){
                                        stock_container.html(stock);
                                    }

                                } else if (inventory_policy === 'never'){
                                    if (stock !== 0) {
                                        stock_container.html(stock);
                                    } else {
                                        stock_container.html("On Demand");
                                    }

                                    grade_label.find('input').prop('disabled', false);
                                    grade_label.find('input').prop('max', 1000);
                                }


                        }


                    } else {

                        var dialog = new Dialog(this, {
                            size: 'medium',
                            dialogClass: 'o_act_window',
                            title: _t("Connection Error"),
                            $content: $(_t("<span class='text-center' style='padding: 2rem;'>Error fetching products information. Please, try again later.</span>"))
                        });
                        dialog.open();

                    }
                }); // END then function


        }  // END if



        /* Handle layout list options */
        $(document).on('click', '.o_wsale_apply_list', function(event) {
            event.preventDefault();
            $('#grid').removeClass('active');
            $('#list').addClass('active');
            // Apply specs filter css
            let specs_filters = $(".oct_filter_wrapper");
            specs_filters.each(function () {
                let add_class = "col-lg-8 col-md-8";
                let remove_class = "col-lg-12 col-md-12";
                specs_filters.removeClass(remove_class);
                specs_filters.addClass(add_class);
                let oct_filters = $(this).find('.oct_filters');
                oct_filters.removeClass('oct_filters_grid_mode');
                oct_filters.addClass('oct_filters_list_mode');
            })
        }); // END LAYOUT LIST OPTIONS

        /* Handle layout grid options */
        $(document).on('click', '.o_wsale_apply_grid', function(event) {
            event.preventDefault();
            $('#list').removeClass('active');
            $('#grid').addClass('active');
            // Apply specs filter css
            let specs_filters = $(".oct_filter_wrapper");
            specs_filters.each(function () {
                let add_class = "col-lg-12 col-md-12";
                let remove_class = "col-lg-8 col-md-8";
                specs_filters.removeClass(remove_class);
                specs_filters.addClass(add_class);
                let oct_filters = $(this).find('.oct_filters');
                oct_filters.removeClass('oct_filters_list_mode');
                oct_filters.addClass('oct_filters_grid_mode');

            })
        }); // END LAYOUT GRID OPTIONS

        /* Filter product brands */
        $(document).on('change', '.js_product_brands', function(event) {
            if (!event.isDefaultPrevented()) {
                event.preventDefault();
                $(this).closest("form").submit();
            }
        }); // END FILTER PRODUCT BRANDS


         // GRADE CONTAINER ON PRODUCT DETAIL
        /* $(document).on('change', '.oct_grade_container_detail',function (e) {
            console.log("GRADE RADIO CHANGED");
            /!* select filter values *!/
            let grade = $(this).find("input:radio[name=optradio]:checked").val();
            console.log(grade);

            // vars on product grid or product detail
            var parent_container = $(this).parents('#product_details');
            var product_id = $("input[name='product_id']").val();


            // parent_container.find(".js_add_cart_update").show();


            // console.log(parent_container);
            // console.log("PRODUCT ID: " + product_id);

            // let load_color_spinner = $("<i class=\"fa fa-spinner fa-spin\"/> <span>Loading colors...</span>");

            // $(quant_container).html(spinner);
            // var colors_container = parent_container.find(".colors");
            // var ul_container = colors_container.find("ul");
            // ul_container.html(load_color_spinner);
            // colors_container.removeClass('oct_hidden');

            var specs = parent_container.find('.specs_selected').data('specs');

            ajax.jsonRpc('/shop/get_product_info/detail', 'call', {
                product_id: product_id,
                grade: grade
            }).then(function (data) {
            if (data) {
                console.log(data);
                console.log("Product ID: " + product_id + ', Grade: ' + grade)
            } else {

            }
        });

        }); // END PRODUCT SPECIFICATIONS HANDLER ON PRODUCT DETAIL*/

        // Grade Container on GRID
        $(document).on('change', '.oct_grade_container',function (e) {
            console.log("GRADE RADIO CHANGED");
            /* select filter values */
            let grade = $(this).find("input:radio[name=optradio]:checked").val();
            console.log(grade);

            // vars on product grid or product detail
            if ($('#products_grid').length > 0){
                var parent_container = $(this).parents('.o_wsale_product_information');
                console.log(parent_container);
                var product_id = parent_container.find("input[name='product_id']").val();   //parent_container.find('a').data('oe-id');
                var qty_input = parent_container.find('.input_add_qty');
            } else { // vars on product detail
                var parent_container = $(this).parents('#product_details');
                var product_id = $("input[name='product_id']").val();
            }
            var inventory_policy = parent_container.find('.oct_stock_qty').data('inventory-policy')

            var available_threshold = parseInt(parent_container.find('.oct_stock_qty').data('inventory-threshold'));
            var specs = parent_container.find('.specs_selected').data('specs');
            var quant_paragraph =  parent_container.find('.specs_paragraph');

            // Color selector grid
            var load_color_spinner = $("<i class=\"fa fa-spinner fa-spin\"/> <span>Loading colors...</span>");
            var colors_container = parent_container.find(".colors");
            var ul_container = colors_container.find("ul");
            ul_container.html(load_color_spinner);
            colors_container.removeClass('oct_hidden');

            var no_specs_selected_msg = parent_container.find('.no_specs');


            ajax.jsonRpc('/shop/get_product_info/grid', 'call', {
                product_id: product_id,
                grade: grade,
                specs: specs
            }).then(function (data) {
            if (data) {
                console.log(data);
                // ul_container.html("");
                console.log("Product ID: " + product_id + ', Grade: ' + grade + ', Cart QTY: ' + data.cart_qty)
                var grade_quant = data.grade_quant;
                var available_quant = grade_quant - data.cart_qty
                var specs_quant_container = parent_container.find('.specs_quant');
                specs_quant_container.html(grade_quant);
                quant_paragraph.removeClass('oct_hidden');
                console.log("AVAILABLE QUANT.....")
                console.log(available_quant)
                var specs_cart_container = quant_paragraph.find('.specs_cart_qty_container');
                var specs_cart_qty = specs_cart_container.find('.specs_cart_qty');


                // Color selector grid
                ul_container.html("");
                for (var index in data.color.color_data){

                    console.log(data.color.color_data[index][0]);
                    console.log(data.color.color_data[index][1]);

                    var color_id = data.color.color_data[index][0];
                    var color_index = data.color.color_data[index][1];
                    var color_name = data.color.color_data[index][2];
                    var color_quantity = data.color.color_data[index][3];

                    if (inventory_policy === 'threshold'){
                        if (color_quantity > available_threshold){
                            color_quantity = 'Available'
                        }

                    }

                    var html_list = '<li><label class="color_label"><input type="radio" data-qty="'+ color_quantity  +'" name="color" value="'+ color_id + '"/><span class="swatch" style="background-color:' + color_index + ';"></span>' + color_name + ' (' + color_quantity + ')' + '</label></li>'
                    ul_container.append(html_list);
                }

                no_specs_selected_msg.hide();



                if (data.cart_qty > 0){
                    specs_cart_qty.html(data.cart_qty);
                    specs_cart_container.removeClass('oct_hidden');
                } else {
                    specs_cart_qty.html(data.cart_qty);
                    specs_cart_container.addClass('oct_hidden');
                }



                if (inventory_policy === 'always'){

                    qty_input.prop('max', available_quant)
                    quant_paragraph.find('.specs_quant').html(available_quant)

                } else if (inventory_policy === 'never'){

                    qty_input.prop('max', 1000)
                    if (available_quant !== 0){
                        quant_paragraph.find('.specs_quant').html(available_quant)
                    } else {
                        quant_paragraph.find('.specs_quant').html("On Demand")
                    }


                } else if (inventory_policy === 'threshold'){
                    console.log("THRESHOLD")

                    qty_input.prop('max', available_quant)

                    if (available_quant > available_threshold){
                        quant_paragraph.find('.specs_quant').html("Available")

                    } else  if (available_quant < available_threshold){
                        quant_paragraph.find('.specs_quant').html(available_quant)
                    }


                }

            } else {

            }
        });

        }); // END PRODUCT SPECIFICATIONS HANDLER

        // Colors handler grid
        $(document).on('change', '.colors', function (ev) {
            ev.stopPropagation();
            // vars on product grid or product detail
            if ($('#products_grid').length > 0){
                var parent_container = $(this).parents('.o_wsale_product_information');
                var qty_input = parent_container.find('.input_add_qty');
                var specs = parent_container.find('.specs_selected').data('specs');
                var specs_data = process_specs(specs);
                var specs_quant_container = parent_container.find('.specs_quant');
                var quant_paragraph =  parent_container.find('.specs_paragraph');
            } else { // vars on product detail
                var parent_container = $(this).parents('#product_details');
                var qty_input = parent_container.find('.quantity');

                var lock_status = parent_container.find("select[name='lock_status']").children("option:selected").val();
                var logo = parent_container.find("select[name='logo']").children("option:selected").val();
                var charger = parent_container.find("select[name='charger']").children("option:selected").val();
                var applications = parent_container.find("select[name='applications']").children("option:selected").val();
                var specs_data = {
                    lock_status: lock_status,
                    logo: logo,
                    charger: charger,
                    applications: applications}
                var specs_quant_container = parent_container.find('.oct_product_qty');
                var quant_paragraph =  parent_container.find('.quant_specs_paragraph');

            }

            // parent_container.find(".js_add_cart_update").show();
            // parent_container.find(".o_wsale_product_btn").show();

            // var max_color_qty = $(this).find("input:radio[name=color]:checked").data('qty');
            //
            // console.log(max_color_qty);
            // qty_input.prop('max', max_color_qty)

            console.log("COLOR CHANGED.....")
            var grade = parent_container.find("input:radio[name=optradio]:checked").val();
            console.log("GRADE: " + grade);
            var color = parent_container.find("input:radio[name=color]:checked").val();
            console.log("COLOR: " + color)

            var product_id = parent_container.find("input[name='product_id']").val();
            var inventory_policy = parent_container.find('.oct_stock_qty').data('inventory-policy')
            var available_threshold = parseInt(parent_container.find('.oct_stock_qty').data('inventory-threshold'));



            ajax.jsonRpc('/shop/get_product_info', 'call', {
                product_id: product_id,
                grade: grade,
                color: color,
                lock_status: specs_data.device_lock_status,
                logo: specs_data.device_logo,
                charger: specs_data.device_charger,
                applications: specs_data.device_applications

            }).then(function (data) {
                if (data) {
                    console.log(data);
                    var cart_qty = data.cart_qty;

                    var available_quant = data.product_quants - cart_qty


                    if (inventory_policy === 'threshold'){
                        if (available_quant <= available_threshold){
                            specs_quant_container.html(available_quant);
                        } else {
                            specs_quant_container.html("Available");
                        }

                    } else {
                        specs_quant_container.html(available_quant);
                    }

                    // quant_paragraph.removeClass('oct_hidden');
                    console.log("AVAILABLE QUANT.....")
                    console.log(available_quant)
                    var specs_cart_container = quant_paragraph.find('.specs_cart_qty_container');
                    var specs_cart_qty = specs_cart_container.find('.specs_cart_qty');

                    if (data.cart_qty > 0){
                        specs_cart_qty.html(data.cart_qty);
                        specs_cart_container.removeClass('oct_hidden');
                    } else {
                        specs_cart_qty.html(data.cart_qty);
                        specs_cart_container.addClass('oct_hidden');
                    }

                    qty_input.prop('max', available_quant)
                }
            });

        }); // END Colors handler


        /* Product Detail specifications handler */
        $(document).on('change', '.oct_grid_variant_selector',function (e) {
            /* select filter values */
            // let grade = $(this).find("select[name='grade']").children("option:selected").val();
            // let color = $(this).find("select[name='color']").children("option:selected").val();
            let lock_status = $(this).find("select[name='lock_status']").children("option:selected").val();
            let logo = $(this).find("select[name='logo']").children("option:selected").val();
            let charger = $(this).find("select[name='charger']").children("option:selected").val();
            // let network_type = $(this).find("select[name='network_type']").children("option:selected").val();
            // let lang = $(this).find("select[name='lang']").children("option:selected").val();
            let applications = $(this).find("select[name='applications']").children("option:selected").val();

            // vars on product detail
            var parent_container = $(this).parents('#product_details');
            var product_id = $("input[name='product_id']").val();
            var price_container =  parent_container.find('.oe_currency_value');
            var quant_container =  parent_container.find('.oct_product_qty');
            var quant_paragraph =  parent_container.find('.quant_specs_paragraph');
            var qty_input = $("input[name='add_qty']");
            var add_to_cart_button = $('#add_to_cart_json');

            var inventory_policy = parent_container.find('.oct_stock_qty').data('inventory-policy');

            var available_threshold = parseInt(parent_container.find('.oct_stock_qty').
                data('inventory-threshold'));

            let grade = parent_container.find("input:radio[name=optradio]:checked").val();
            console.log("GRADE: " + grade)

            console.log("PRODUCT ID: " + product_id);

            let spinner = $("<i class=\"fa fa-spinner fa-spin\"/>");

            $(quant_container).html(spinner);
            $(quant_paragraph).removeClass('oct_hidden');


            var load_color_spinner = $("<i class=\"fa fa-spinner fa-spin\"/> <span>Loading colors...</span>");
            var colors_container = parent_container.find(".colors");
            var ul_container = colors_container.find("ul");
            ul_container.html(load_color_spinner);
            colors_container.removeClass('oct_hidden');

            var color = 0;


            ajax.jsonRpc('/shop/get_product_info', 'call', {
                product_id: product_id,
                grade: grade,
                color: color,
                lock_status: lock_status,
                logo: logo,
                charger: charger,
                // network_type: network_type,
                // lang: lang,
                applications: applications
            }).then(function (data) {
            if (data) {

                ul_container.html("");
                for (var index in data.color.color_data){

                    console.log(data.color.color_data[index][0]);
                    console.log(data.color.color_data[index][1]);

                    var color_id = data.color.color_data[index][0];
                    var color_index = data.color.color_data[index][1];
                    var color_name = data.color.color_data[index][2];
                    var color_quantity = data.color.color_data[index][3];

                    if (inventory_policy === 'threshold'){
                        if (color_quantity > available_threshold){
                            color_quantity = 'Available'
                        }

                    }

                    var html_list = '<li><label class="color_label"><input type="radio" data-qty="'+ color_quantity  +'" name="color" value="'+ color_id + '"/><span class="swatch" style="background-color:' + color_index + ';"></span>' + color_name + ' (' + color_quantity + ')' + '</label></li>'
                    ul_container.append(html_list);
                }

                console.log("DATA FROM CONTROLLER")
                console.log(data);
                var available_quant = data.product_quants - data.cart_qty

                console.log(inventory_policy)

                if (inventory_policy === 'never') {

                    if (available_quant === 0){
                        console.log("AVAILABLE = 0")
                        $(quant_container).html("On Demand");
                    } else {
                        $(quant_container).html(available_quant);
                    }

                    qty_input.attr({'max': 1000});

                } else if (inventory_policy === 'always') {

                    qty_input.attr({'max': available_quant});
                    $(quant_container).html(available_quant)
                    $(quant_container).html(available_quant)


                } else if (inventory_policy === 'threshold') {

                    if (available_quant > available_threshold){
                        $(quant_container).html("Available");
                    } else if (available_quant < available_threshold) {
                        $(quant_container).html(available_quant);
                    }
                    qty_input.attr({'max': available_quant});

                }

                var specs_cart_container = quant_paragraph.find('.specs_cart_qty_container');
                var specs_cart_qty = specs_cart_container.find('.specs_cart_qty');
                if (data.cart_qty > 0){
                    specs_cart_qty.html(data.cart_qty);
                    specs_cart_container.removeClass('oct_hidden');
                } else {
                    specs_cart_qty.html(data.cart_qty);
                    specs_cart_container.addClass('oct_hidden');
                }

                /*var new_price = data.product_price;
                $(price_container).each(function () {
                    $(this).text(new_price);
                });
                $(quant_container).html(data.product_quants);

                if (data.product_quants > 0 && grade !== "0"){
                    qty_input.prop( "disabled", false );
                    qty_input.attr({'max': data.product_quants});
                    add_to_cart_button.removeClass('oct_hidden_important');
                } else {
                    qty_input.prop( "disabled", true );
                    add_to_cart_button.addClass('oct_hidden_important');
                }*/

            } else {

            }
        });

        }); // END PRODUCT SPECIFICATIONS HANDLER

        /* Specifications filter toggle visualization handler */
        $(document).on('click', '.oct_filter_title', function(ev){
            var filter_container = $(this).parents('.oct_grid_variant_selector').find('.oct_filters');
            var selector_icon = $(this).parents('.oct_grid_variant_selector').find('.oct_selector_icon');
            $(this).parents('.oct_grid_variant_selector').find('.oct_filters').toggle("slow", function () {
                if (filter_container.is(":visible")){
                    selector_icon.html("<i class=\"fa fa-caret-up\"/>");
                } else {
                    selector_icon.html("<i class=\"fa fa-caret-down\"/>");
                }
            });
        });


        /* Cart specifications lines remove handler */
        $(document).on('click', '.remove_specs_line', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            // get line variables
            var action_icon = $(this).find("i");
            var spinner_icon = $("<i class=\"fa fa-spinner fa-spin\"/>");
            var error_icon = $("<i class='fa fa-ban/>'");
            var specs_id =  $(this).data('specs-id');
            var specs_qty =  parseInt($(this).data('specs-qty'));
            var product_row = $("#" + $(this).data('product-row'));
            var product_total_qty_container = product_row.find('.total_product_qty');
            var product_total_qty =  parseInt(product_total_qty_container.text());
            var specs_row =  $(this).closest('tr');
            var order_line_specs_row =  $(this).closest('.order_line_specs_row');
            var cart_table = $("#cart_products");

            console.log(product_row);
            // console.log(product_total_qty_container);
            console.log(product_total_qty);
            // console.log(order_line_specs_row);
            // console.log(cart_table);

            action_icon.html(spinner_icon);

            ajax.jsonRpc('/shop/cart/delete_specs', 'call', {
                    specs_id: specs_id,
                    specs_qty: specs_qty
                }).then(function (data) {
                    if (data) {
                        if (data.success === 'true'){
                            specs_row.remove();
                            var new_qty = product_total_qty - specs_qty;

                            console.log("New qty: " + new_qty);

                            if (new_qty > 0){
                                console.log("new qty GT 0");
                                // product_total_qty = new_qty;
                                product_total_qty_container.text(new_qty);
                            } else {
                                console.log("new qty EQ 0");
                                order_line_specs_row.remove();
                                product_row.remove();
                            }

                            // reload window if no more lines in the cart.
                            if (data.remain_lines === 0){
                                // cart_table.remove();
                                window.location.reload();
                            }
                            console.log(data.canon_info);
                            if (data.canon_info){
                                for (var canon_id in data.canon_info){
                                    var canon_line = $("#canon_row_" + canon_id);
                                    console.log(canon_line)
                                    var canon_qty_container = canon_line.find('.total_product_qty')
                                    canon_qty_container.html(data.canon_info[canon_id])
                                }
                            }

                        } else {
                            // show an error message
                            action_icon.html(error_icon);
                        }

                    } else {

                    }
                });

        })

        $(document).on('change', '.oct_price_offered', function () {
            console.log("PRICE OFFERED CHANGED");

            var error_dialog = new Dialog(this, {
                size: 'medium',
                dialogClass: 'o_act_window',
                title: _t("Offer error"),
                $content: $(_t("<span class='text-center' style='padding: 2rem;'> Your offer have not been processed. Please, try again later.</span>"))
            });

            var spinner_container = $(this).parents('tr').find('.spinner_container');
            var line_id = $(this).data('line-id');
            var offer_value = $(this).val();

            let spinner = $("<i class=\"fa fa-spinner fa-spin\"/>");
            spinner_container.html(spinner);

            ajax.jsonRpc('/shop/cart/update_price_offered', 'call', {
                line_id: line_id,
                offer: offer_value
            }).then(function (data) {
                console.log(data);
                if (data.response === 'done'){
                    console.log("OFFER SENT.....")
                    spinner_container.html('')
                } else {
                    spinner_container.html('')
                    error_dialog.open();
                }
            }); // END AJAX call

        });











            } else {  // END GET WEBSITE FOR SELL

                console.log("OTHER WEBSITE.....")
                // Get variant attribute qty
                if ($("#product_detail").length > 0) {
                    var parent_container = $("#product_detail");
                    var product_tmpl_id = parent_container.find("input[name='product_template_id']").val();
                    console.log("PRODUCT DETAIL PAGE")
                    console.log(product_tmpl_id)
                    ajax.jsonRpc('/shop/get_product_variant_quant_info', 'call', {
                            product_template_id: product_tmpl_id
                        }).then(function (data) {

                        if (data) {
                            console.log(data);
                            for (var key in data){
                                var input = parent_container.find("input[value="+ key + "]")
                                var select_option = parent_container.find("select.js_variant_change option[value="+ key +"]")
                                console.log(key)
                                console.log(input)
                                console.log(select_option)

                                var content_qty = $("<span class='oct_variant_qty'>(" + data[key] + ")</span>")

                                if (input.length){
                                    // var content_qty = $("<i class='fa fa-cubes'/> Stock: <span class='oct_variant_qty'>" + data[key] + "</span>")
                                    content_qty.insertAfter(input.parents('label'))
                                } else if(select_option.length) {
                                    console.log("SELECTION OPTION")
                                    select_option.html( select_option.html() + "("+ data[key] + ")")
                                }

                            }
                        }
                    });

                }


            } // END OTHERS WEBSITES







        });

        /* Default price and stock hidden */
  /*      if ($('#products_grid').length > 0){
            $(".oe_product").each(function () {
                /!*var selector = $(this).find('.oct_grade');
                selector.find('option[value="5"]').attr("selected",true);
                selector.trigger('change');*!/
                $(".product_price").addClass("oct_hidden");
                $(".oct_stock_qty").addClass("oct_hidden");
                $(".js_add_cart_update").addClass("oct_hidden_important");
            });
        } else if ($("#product_detail").length > 0) {
            $(this).find(".product_price").addClass("oct_hidden");
            $(this).find(".oct_stock_qty").addClass("oct_hidden");
            $(this).find(".js_add_cart_update").addClass("oct_hidden_important");
        }*/

        function process_specs(specs_string) {
            return JSON.parse(specs_string.replace(/'/g,"\""))
        }

    }) // END DOCUMENT READY

}); // END ODOO DEFINE