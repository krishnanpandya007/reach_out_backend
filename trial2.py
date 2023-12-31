import qrcode
import base64
from io import BytesIO

message = "36b6eb6ca1434b6a9c875b9517cda5ad:36b6eb6ca1434b6a9c875b9517cda5ad"

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=1,
)
qr.add_data(message)
qr.make(fit=True)

img_buffer = BytesIO()
qr.make_image(fill_color="#3CCF4E", back_color="white").save(img_buffer)

qr_code_bytes = img_buffer.getvalue()

qr_code_base64 = base64.b64encode(qr_code_bytes).decode("utf-8")

data_uri_scheme = f"data:image/png;base64,{qr_code_base64}"

print("Data URI Scheme for the QR Code:")
print(data_uri_scheme)
