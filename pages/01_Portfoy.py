import streamlit as st
import pandas as pd

from modules.data.yahoo_data import (
    get_history,
    get_last_price
)


st.set_page_config(
    page_title="Portföy",
    page_icon="📊",
    layout="wide"
)


st.title("📊 Portföy Yönetimi")


st.subheader("📥 Excel Portföy Aktar")


uploaded_file = st.file_uploader(
    "Excel dosyanızı seçin",
    type=["xlsx"]
)


if uploaded_file:


    excel = pd.ExcelFile(uploaded_file)


    st.success(
        f"{len(excel.sheet_names)} adet hisse sayfası bulundu"
    )


    tum_islemler = []


    for sheet in excel.sheet_names:


        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet
        )


        if not df.empty:


            df["Hisse"] = sheet.upper()

            tum_islemler.append(df)



    if tum_islemler:


        portfoy_df = pd.concat(
            tum_islemler,
            ignore_index=True
        )


        st.divider()


        st.subheader(
            "📋 İşlem Listesi"
        )


        st.dataframe(
            portfoy_df,
            use_container_width=True
        )



        st.divider()


        st.subheader(
            "📈 Portföy Özeti"
        )


        sonuc = []



        for hisse, grup in portfoy_df.groupby("Hisse"):


            lot = 0

            toplam_maliyet = 0



            for _, row in grup.iterrows():


                islem = str(
                    row["İşlem"]
                ).upper()


                adet = float(
                    row["Adet"]
                )


                fiyat = float(
                    row["Fiyat"]
                )



                if "AL" in islem:


                    lot += adet


                    toplam_maliyet += (
                        adet * fiyat
                    )



                elif "SAT" in islem:


                    lot -= adet




            if lot > 0:



                ortalama = (

                    toplam_maliyet / lot

                )



                # ==========================
                # GÜNCEL FİYAT
                # ==========================


                try:


                    sembol = hisse.upper()


                    if not sembol.endswith(".IS"):

                        sembol = sembol + ".IS"



                    fiyat_df = get_history(
                        sembol
                    )



                    guncel_fiyat = get_last_price(
                        fiyat_df
                    )


                    if guncel_fiyat is None:

                        guncel_fiyat = 0



                except Exception as e:


                    st.warning(
                        f"{hisse} fiyat hatası: {e}"
                    )


                    guncel_fiyat = 0




                portfoy_degeri = (

                    lot * guncel_fiyat

                )




                if ortalama > 0 and guncel_fiyat > 0:


                    kz = (

                        (guncel_fiyat - ortalama)

                        /

                        ortalama

                    ) * 100



                else:


                    kz = 0




                sonuc.append(

                    {

                        "Hisse": hisse,

                        "Lot": lot,

                        "Ortalama Maliyet": round(
                            ortalama,
                            2
                        ),

                        "Güncel Fiyat": round(
                            guncel_fiyat,
                            2
                        ),

                        "Portföy Değeri": round(
                            portfoy_degeri,
                            2
                        ),

                        "K/Z %": round(
                            kz,
                            2
                        )

                    }

                )



        if sonuc:


            sonuc_df = pd.DataFrame(
                sonuc
            )


            st.dataframe(
                sonuc_df,
                use_container_width=True
            )



            toplam_deger = sonuc_df[
                "Portföy Değeri"
            ].sum()



            st.metric(
                "💰 Toplam Portföy Değeri",
                f"{toplam_deger:,.2f} TL"
            )



        else:


            st.warning(
                "Aktif portföy bulunamadı."
            )



    else:


        st.warning(
            "Excel verisi okunamadı."
        )