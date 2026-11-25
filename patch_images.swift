import Cocoa
import Vision

// Fast Phone Number Patcher for Blog Images
let targetPhone = "010-5615-2118"

func patchImageSmart(fileURL: URL) -> (Bool, String) {
    guard let nsImage = NSImage(contentsOf: fileURL) else { return (false, "Cannot open image") }
    guard let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return (false, "Cannot get cgImage") }
    
    let width = cgImage.width
    let height = cgImage.height
    
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ko-KR", "en-US"]
    
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    do {
        try handler.perform([request])
    } catch {
        return (false, "OCR failed: \(error)")
    }
    
    guard let results = request.results, !results.isEmpty else { return (false, "No text") }
    
    var matches = [(String, CGRect)]()
    for obs in results {
        if let cand = obs.topCandidates(1).first {
            let str = cand.string
            // Check for phone number patterns that need replacement
            let hasPhone = str.contains("010") || str.contains("2340") || str.contains("4211") || str.contains("4437") || str.contains("2118")
            if hasPhone {
                if !str.contains(targetPhone) && !str.contains("010 5615 2118") {
                    matches.append((str, obs.boundingBox))
                }
            }
        }
    }
    
    if matches.isEmpty { return (false, "No phone match") }
    
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    guard let context = CGContext(data: nil,
                                  width: width,
                                  height: height,
                                  bitsPerComponent: 8,
                                  bytesPerRow: width * 4,
                                  space: colorSpace,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
        return (false, "Cannot create CGContext")
    }
    
    context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    guard let pixelData = context.data else { return (false, "No pixel data") }
    
    var patchedTexts = [String]()
    for (text, normRect) in matches {
        let rect = CGRect(x: normRect.origin.x * CGFloat(width),
                          y: normRect.origin.y * CGFloat(height),
                          width: normRect.size.width * CGFloat(width),
                          height: normRect.size.height * CGFloat(height))
        
        let sampleX = Int(min(max(0, rect.origin.x - 4), CGFloat(width - 1)))
        let sampleY = Int(min(max(0, rect.origin.y - 4), CGFloat(height - 1)))
        let offset = (sampleY * width + sampleX) * 4
        let r = CGFloat(pixelData.load(fromByteOffset: offset, as: UInt8.self)) / 255.0
        let g = CGFloat(pixelData.load(fromByteOffset: offset + 1, as: UInt8.self)) / 255.0
        let b = CGFloat(pixelData.load(fromByteOffset: offset + 2, as: UInt8.self)) / 255.0
        
        let luminance = 0.299 * r + 0.587 * g + 0.114 * b
        let isDark = luminance < 0.5
        
        let paddedRect = rect.insetBy(dx: -4, dy: -4)
        
        let bgColor = isDark ? CGColor(red: r, green: g, blue: b, alpha: 1.0) : CGColor(red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0)
        context.setFillColor(bgColor)
        context.fill(paddedRect)
        
        let newText: String
        if text.contains("문의") {
            newText = "문의:\(targetPhone)"
        } else {
            newText = targetPhone
        }
        
        let textColor = isDark ? NSColor.white : NSColor.black
        let fontSize = paddedRect.height * 0.75
        let font = NSFont(name: "AppleSDGothicNeo-Bold", size: fontSize) ?? NSFont.boldSystemFont(ofSize: fontSize)
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: textColor
        ]
        let attrStr = NSAttributedString(string: newText, attributes: attrs)
        let line = CTLineCreateWithAttributedString(attrStr)
        
        let textWidth = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        let textX = paddedRect.origin.x + (paddedRect.width - textWidth) / 2.0
        let textY = paddedRect.origin.y + (paddedRect.height - fontSize) / 2.0 + 2
        
        context.textPosition = CGPoint(x: textX, y: textY)
        CTLineDraw(line, context)
        patchedTexts.append("\(text) -> \(newText)")
    }
    
    guard let outCG = context.makeImage() else { return (false, "Cannot export CGImage") }
    let rep = NSBitmapImageRep(cgImage: outCG)
    guard let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.92]) else { return (false, "Cannot encode JPEG") }
    
    do {
        try data.write(to: fileURL)
        return (true, patchedTexts.joined(separator: ", "))
    } catch {
        return (false, "Write failed: \(error)")
    }
}

// CLI Driver
let args = CommandLine.arguments
let fm = FileManager.default

var targetFiles = [URL]()
if args.count > 1 {
    let mode = args[1]
    if mode == "--covers" {
        let blogImages = URL(fileURLWithPath: "blog/images")
        if let dirs = try? fm.contentsOfDirectory(atPath: blogImages.path) {
            for d in dirs {
                let u = blogImages.appendingPathComponent(d).appendingPathComponent("cover.jpg")
                if fm.fileExists(atPath: u.path) {
                    targetFiles.append(u)
                }
            }
        }
    } else if mode == "--all" {
        let blogImages = URL(fileURLWithPath: "blog/images")
        if let dirs = try? fm.contentsOfDirectory(atPath: blogImages.path) {
            for d in dirs {
                let dirURL = blogImages.appendingPathComponent(d)
                if let files = try? fm.contentsOfDirectory(atPath: dirURL.path) {
                    for f in files where f.hasSuffix(".jpg") || f.hasSuffix(".png") {
                        targetFiles.append(dirURL.appendingPathComponent(f))
                    }
                }
            }
        }
    } else {
        targetFiles.append(URL(fileURLWithPath: mode))
    }
} else {
    print("Usage: patch_images [--covers | --all | <path>]")
    exit(1)
}

print("Loaded \(targetFiles.count) files to process...")

let total = targetFiles.count
var patchedCount = 0
let lock = NSLock()
let startTime = Date()

DispatchQueue.concurrentPerform(iterations: total) { idx in
    let u = targetFiles[idx]
    let (success, detail) = patchImageSmart(fileURL: u)
    if success {
        lock.lock()
        patchedCount += 1
        print("[\(patchedCount)] Patched \(u.path): \(detail)")
        lock.unlock()
    }
    
    if idx % 100 == 0 && idx > 0 {
        lock.lock()
        let elapsed = Date().timeIntervalSince(startTime)
        print("Progress: \(idx)/\(total) processed (\(String(format: "%.1f", elapsed))s, \(patchedCount) patched)")
        lock.unlock()
    }
}

let totalElapsed = Date().timeIntervalSince(startTime)
print("==================================================")
print("Done! Total files: \(total), Patched: \(patchedCount) in \(String(format: "%.1f", totalElapsed))s")
print("==================================================")
