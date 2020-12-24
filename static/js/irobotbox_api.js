    function mass_read_sku_info(sku_list, acsi, user_name, user_password){
        sku_list = sku_list.join(",")
        var ev = `<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<GetProducts xmlns="http://tempuri.org/">
<productRequest>
<CustomerID>1551</CustomerID>
<UserName>${user_name}</UserName>
<Password>${user_password}</Password>
<ClientSKUs>${sku_list}</ClientSKUs>
</productRequest>
</GetProducts>
</soap:Body>
</soap:Envelope>`

        var headers = {"content-type" : "text/xml; charset=utf-8"}
        var url = "/redirect_to_erp"
        $.ajax({
            type: "POST",
            url:url,
            headers:headers,
            data: ev,
            dataType: "xml",
            success:function(res){
                //console.log(res)
                var row_list = $("ApiProductInfo", res).toArray();
                var ob_row_list = []
                for (let row of row_list){
                    let ob_row = {};
                    for (let ce of row.children){
                        let k = ce.tagName
                        let v = ce.textContent
                        ob_row[k] = v

                    }
                    ob_row["ImageList"] = $("ImageUrl", row).toArray().map(i=>i.textContent)
                    ob_row["Cover"] = $("ApiProductImage", row).toArray().filter(i=>i.innerHTML.indexOf("true")>0)[0]
                    ob_row["Cover"] = $("ImageUrl", ob_row["Cover"])[0].textContent
                    ob_row_list.push(ob_row)
                }
                $.get("/get_sufix", function(res){
                    sufix = res.data
                ob_row_list.map(i => {flag.data.push(convertRow(i,acsi, sufix))})
                flag.sku_list_count -= 1
                if (flag.sku_list_count == 0){
                    flag.data.sort((i, j)=>Number(i[0])>Number(j[0]))
                    data2book(flag.data, acsi)
                }                    
                })
            }})
    }
    function convertRow(row, acsi, sufix){
        var site = acsi.split(".")[1]
        var acc = acsi.split(".")[0]
        row.ProductDescription = row.ProductDescription.replace(new RegExp("<br />\n","gm"), "\r\n")
        row.ProductDescription = row.ProductDescription.replace(new RegExp("<br />","gm"), "\r\n")
        //row.ProductDescription = row.ProductDescription.replace(new RegExp('"',"gm"), '""')
        row.ProductDescription = row.ProductDescription.replace("Specif", "\r\nSpecif")
        row.ProductDescription = row.ProductDescription.replace("Note", "\r\nNote")
        row.ProductDescription = row.ProductDescription.replace("Package", "\r\nPackage")

        var sfname = sufix[acc][0]
        row.ProductName  += sfname
        var sfdes = "\r\n\r\n" + sufix[acc][2].split(",").join("\r\n")
        row.ProductDescription += sfdes
        var location = ["nw", "sw", "ne", "se"][Math.floor(Math.random()*4)]
        var base = sufix[acc][1]
        var sfimg = `?x-oss-process=image/watermark,size_80,color_FFFFFF,t_5,shadow_5,g_${location},text_${base}`
        row.ImageList = row.ImageList.map(i => i + sfimg)
        var cost = Number(row.LastSupplierPrice)
        var weight = Number(row.GrossWeight)
        row.sprice = calculate_price(cost, weight, 0.2)[site]
        if (site == "br"){row.sprice *= 0.9}
        var cut = {"my":0.1, "id":100, "th":1, "ph":1, "vn":100, "br":0.1, "sg": 0.1}
        row.sprice = Math.floor(row.sprice /0.6 / cut[site]) * cut[site]

        var urow = new Array(28).fill("")
        urow[0] = row.SKU
        urow[1] = row.ProductName
        urow[2] = row.ProductDescription
        urow[10] = row.sprice
        urow[11] = 300
        urow[22] = row.GrossWeight
        urow[26] = "开启"
        for (let i = 0; i < Math.min(9, row.ImageList.length); i++){urow[13 + i] = row.ImageList[i];}
        if (site != "vn"){urow[22] = Math.ceil(urow[22]/10) / 100}
        if (row.ClientSKU.indexOf("-00") > -1 || row.ClientSKU.indexOf("-") == -1){
            urow[3] = row.ClientSKU
        }else {
            var psk = row.ClientSKU.split("-")[0]
            urow[3] = psk
            urow[4] = psk
            urow[5] = "color"
            urow[6] = "No." + row.ClientSKU.split("-")[1].slice(0, 2)
            urow[7] = row.Cover + sfimg
            urow[12] = row.ClientSKU
        }
        //urow[1] = '"' + urow[1] + '"'
        //urow[2] = '"' + urow[2] + '"'
        //row.ProductNameCN = '"' + row.ProductNameCN + '"'
        urow.push(row.ProductNameCN)
        return urow
    }

    //下载资料转化表格
    function data2book(data, acsi){
        var site = acsi.split(".")[1]
        var hd = ["ps_category","ps_product_name","ps_product_description","ps_sku_parent_short",
                  "et_title_variation_integration_no","et_title_variation_1","et_title_option_for_variation_1",
                  "et_title_image_per_variation","et_title_variation_2","et_title_option_for_variation_2",
                  "ps_price","ps_stock","ps_sku_short","ps_item_cover_image",
                  "ps_item_image_1","ps_item_image_2","ps_item_image_3","ps_item_image_4","ps_item_image_5",
                  "ps_item_image_6","ps_item_image_7","ps_item_image_8",
                  "ps_weight","ps_length","ps_width","ps_height","channel_id_78004","ps_product_pre_order_dts"]
        var channel_map = {"my": "channel_id_28016", "id": "channel_id_88001",
                           "th": "channel_id_78004", "ph": "channel_id_48002",
                           "vn": "channel_id_58007", "sg": "channel_id_18025",
                           "br": "channel_id_90001"}
        hd[26] = channel_map[site]
        var rows = [hd,[],[],[],[]]
        var tem = rows.concat(data)
        var dts = [["mass_new_basic"], ["Category name", "Category ID", "Category Pre-order DTS range"]]
        var sheet_data_list = [[],tem,dts,[]]
        var sheet_name_list = ["Guidance", "Template", "Pre-order DTS Range", "Upload Sample"]
        var workbook_upload = XLSX.utils.book_new();

        for (let i=0; i<sheet_data_list.length; i++){
            let sheet = XLSX.utils.aoa_to_sheet(sheet_data_list[i])
            XLSX.utils.book_append_sheet(workbook_upload, sheet, sheet_name_list[i])
        }
        let time_string = Date.now()
        workbook2blob(workbook_upload, "4new_" + acsi + "_" + time_string);
    }
    // 将workbook装化成blob对象
    function workbook2blob(workbook, fileName = "刊登导出") {
        var wopts = {
            bookType: "xlsx",
            bookSST: false,
            type: "binary"
        };
        var wbout = XLSX.write(workbook, wopts);
        function s2ab(s) {
            var buf = new ArrayBuffer(s.length);
            var view = new Uint8Array(buf);
            for (var i = 0; i != s.length; ++i) view[i] = s.charCodeAt(i) & 0xff;
            return buf;
        }
        var blob = new Blob([s2ab(wbout)], {
            type: "application/octet-stream"
        });

        blob = URL.createObjectURL(blob);
        var aLink = document.createElement("a");
        aLink.href = blob;
        aLink.download = fileName + ".xlsx";
        aLink.click();
    }