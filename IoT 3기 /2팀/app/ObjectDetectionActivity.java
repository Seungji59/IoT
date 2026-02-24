package org.pytorch.demo.objectdetection;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.media.Image;
import android.util.Log;
import android.view.TextureView;
import android.view.ViewStub;

import androidx.annotation.Nullable;
import androidx.annotation.WorkerThread;
import androidx.camera.core.ImageProxy;

import org.pytorch.IValue;
import org.pytorch.LiteModuleLoader;
import org.pytorch.Module;
import org.pytorch.Tensor;
import org.pytorch.torchvision.TensorImageUtils;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;

public class ObjectDetectionActivity extends AbstractCameraXActivity<ObjectDetectionActivity.AnalysisResult> {
    private Module mModule = null;
    private ResultView mResultView;

    static class AnalysisResult {
        private final ArrayList<Result> mResults;
        public AnalysisResult(ArrayList<Result> results) { mResults = results; }
    }

    @Override
    protected int getContentViewLayoutId() {
        return R.layout.activity_object_detection;
    }

    @Override
    protected TextureView getCameraPreviewTextureView() {
        mResultView = findViewById(R.id.resultView);
        return ((ViewStub) findViewById(R.id.object_detection_texture_view_stub))
                .inflate()
                .findViewById(R.id.object_detection_texture_view);
    }

    @Override
    protected void applyToUiAnalyzeImageResult(AnalysisResult result) {
        mResultView.setResults(result.mResults);
        mResultView.invalidate();
    }

    /** YUV -> Bitmap 변환 */
    private Bitmap imgToBitmap(Image image) {
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer yBuffer = planes[0].getBuffer();
        ByteBuffer uBuffer = planes[1].getBuffer();
        ByteBuffer vBuffer = planes[2].getBuffer();

        int ySize = yBuffer.remaining();
        int uSize = uBuffer.remaining();
        int vSize = vBuffer.remaining();

        byte[] nv21 = new byte[ySize + uSize + vSize];
        yBuffer.get(nv21, 0, ySize);
        vBuffer.get(nv21, ySize, vSize);
        uBuffer.get(nv21, ySize + vSize, uSize);

        YuvImage yuvImage = new YuvImage(nv21, ImageFormat.NV21, image.getWidth(), image.getHeight(), null);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        yuvImage.compressToJpeg(new Rect(0, 0, yuvImage.getWidth(), yuvImage.getHeight()), 75, out);
        byte[] imageBytes = out.toByteArray();
        return BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);
    }

    /** forward() 결과에서 첫 번째 Tensor를 안정적으로 꺼내기 */
    private Tensor extractFirstTensor(IValue out) {
        if (out == null) return null;
        if (out.isTensor()) return out.toTensor();
        if (out.isTuple()) {
            IValue[] tup = out.toTuple();
            if (tup != null) {
                for (IValue v : tup) {
                    if (v != null && v.isTensor()) return v.toTensor();
                }
            }
        }
        if (out.isList()) {
            IValue[] arr = out.toList();
            if (arr != null) {
                for (IValue v : arr) {
                    if (v != null && v.isTensor()) return v.toTensor();
                }
            }
        }
        return null;
    }

    @Override
    @WorkerThread
    @Nullable
    protected AnalysisResult analyzeImage(ImageProxy image, int rotationDegrees) {
        try {
            if (mModule == null) {
                // ★ CHANGED: MainActivity와 동일한 모델 파일명 사용
                mModule = LiteModuleLoader.load(
                        MainActivity.assetFilePath(getApplicationContext(), "model_v5n_320_20250904_082313.ptl")
                );
            }
        } catch (IOException e) {
            Log.e("ObjectDetection", "Error reading assets", e);
            return null;
        }

        // 카메라 프레임을 Bitmap으로 변환
        Image img = image.getImage();
        if (img == null) return null;
        Bitmap bitmap = imgToBitmap(img);

        // ★ CHANGED: 고정 90도 회전 → 카메라가 준 rotationDegrees 반영
        if (rotationDegrees != 0) {
            Matrix m = new Matrix();
            m.postRotate(rotationDegrees);
            bitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), m, true);
        }

        // 모델 입력 크기로 리사이즈
        Bitmap resizedBitmap = Bitmap.createScaledBitmap(
                bitmap, PrePostProcessor.mInputWidth, PrePostProcessor.mInputHeight, true);

        // 텐서 변환
        final Tensor inputTensor = TensorImageUtils.bitmapToFloat32Tensor(
                resizedBitmap, PrePostProcessor.NO_MEAN_RGB, PrePostProcessor.NO_STD_RGB);

        // ★ CHANGED: 출력 추출을 안전하게 (tuple/list 대비)
        IValue out = mModule.forward(IValue.from(inputTensor));
        Tensor outTensor = extractFirstTensor(out);
        if (outTensor == null) {
            Log.e("ObjectDetection", "No tensor found in model output");
            return null;
        }
        final float[] outputs = outTensor.getDataAsFloatArray();

        // 스케일 계산
        float imgScaleX = (float) bitmap.getWidth()  / PrePostProcessor.mInputWidth;
        float imgScaleY = (float) bitmap.getHeight() / PrePostProcessor.mInputHeight;
        float ivScaleX  = (float) mResultView.getWidth()  / bitmap.getWidth();
        float ivScaleY  = (float) mResultView.getHeight() / bitmap.getHeight();

        // ★ CHANGED: 옛 메서드 → 동적 포맷 처리(postprocessDynamic)로 통일
        final ArrayList<Result> results = PrePostProcessor.postprocessDynamic(
                outputs, imgScaleX, imgScaleY, ivScaleX, ivScaleY, 0, 0
        );

        return new AnalysisResult(results != null ? results : new ArrayList<>());
    }
}
