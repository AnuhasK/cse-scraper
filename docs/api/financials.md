this api url using the post method returns the financial infomation and needs the company symbol as the parameters and returns, 
  - infoAnnualData - annual company data
  - infoQuarterlyData
  - infoWebLink - not needed
  - infoOtherData - has press release data
  - reqFinancial - 
  - infoCompanyBannerAd - not needed

for example if the request is https://www.cse.lk/api/financials?symbol=CALH.N0000

the respose is, 
{
    "infoAnnualData": [
        {
            "id": 48845,
            "path": "cmt/upload_report_file/3319_1756349884006.pdf",
            "manualDate": 1743359400000,
            "uploadedDate": 1756349884006,
            "fileText": "Annual Report 2024/2025",
            "path2": "cmt/upload_report_file/3319_1756349884006.",
            "authorizedDate": null
        }
    ],
    "infoQuarterlyData": [
        {
            "id": 49258,
            "path": "cmt/upload_report_file/3319_1762486123533.pdf",
            "manualDate": 1759170600000,
            "uploadedDate": 1762486123533,
            "fileText": "Interim Financial Statements for the Quarter ended 30th September 2025",
            "path2": "cmt/upload_report_file/3319_1762486123533.",
            "authorizedDate": 1762486217973
        },
        {
            "id": 48620,
            "path": "cmt/upload_report_file/3319_1754997874038.pdf",
            "manualDate": 1751221800000,
            "uploadedDate": 1754997874038,
            "fileText": "Interim Financial Statements for the Quarter ended 30th June 2025",
            "path2": "cmt/upload_report_file/3319_1754997874038.",
            "authorizedDate": null
        },
        {
            "id": 48162,
            "path": "cmt/upload_report_file/3319_1748623331156.pdf",
            "manualDate": 1748543400000,
            "uploadedDate": 1748623331156,
            "fileText": "Interim Financial Statements for the Period Ended  31st March 2025",
            "path2": "cmt/upload_report_file/3319_1748623331156.",
            "authorizedDate": null
        }
    ],
    "infoWebLink": [],
    "infoOtherData": [
        {
            "id": 48163,
            "path": "cmt/upload_report_file/3319_1748623438742.pdf",
            "manualDate": 1748543400000,
            "uploadedDate": 1748623438742,
            "fileText": "Valuation Report - Equity IPO 2025",
            "path2": "cmt/upload_report_file/3319_1748623438742.",
            "authorizedDate": null
        },
        {
            "id": 48161,
            "path": "cmt/upload_report_file/3319_1748623219983.pdf",
            "manualDate": 1748543400000,
            "uploadedDate": 1748623219983,
            "fileText": "Prospectus Annexures - Equity IPO 2025",
            "path2": "cmt/upload_report_file/3319_1748623219983.",
            "authorizedDate": null
        },
        {
            "id": 48160,
            "path": "cmt/upload_report_file/3319_1748623014473.pdf",
            "manualDate": 1748543400000,
            "uploadedDate": 1748623014473,
            "fileText": "Prospectus - Equity IPO 2025",
            "path2": "cmt/upload_report_file/3319_1748623014473.",
            "authorizedDate": null
        }
    ],
    "reqFinancial": [],
    "infoCompanyBannerAd": null
}